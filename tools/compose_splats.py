from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from tools.splat_ply import SplatPly, read_ply, write_ply
except ModuleNotFoundError:
    from splat_ply import SplatPly, read_ply, write_ply


EPS = 1e-6


@dataclass
class Placement:
    scale: float
    rotation_degrees: tuple[float, float, float]
    translation: tuple[float, float, float]


@dataclass
class Appearance:
    opacity_multiplier: float
    dc_color_multiplier: tuple[float, float, float]
    dc_color_bias: tuple[float, float, float]
    sh_rest_multiplier: float


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def logit(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, EPS, 1.0 - EPS)
    return np.log(x / (1.0 - x))


def rotation_matrix_xyz(degrees: tuple[float, float, float]) -> np.ndarray:
    rx, ry, rz = np.deg2rad(np.asarray(degrees, dtype=np.float64))

    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)

    rot_x = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float64)
    rot_y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float64)
    rot_z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float64)
    return rot_z @ rot_y @ rot_x


def quaternion_from_matrix(matrix: np.ndarray) -> np.ndarray:
    m = matrix
    trace = float(np.trace(m))
    if trace > 0.0:
        s = np.sqrt(trace + 1.0) * 2.0
        return np.array(
            [
                0.25 * s,
                (m[2, 1] - m[1, 2]) / s,
                (m[0, 2] - m[2, 0]) / s,
                (m[1, 0] - m[0, 1]) / s,
            ],
            dtype=np.float64,
        )

    if m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2.0
        return np.array(
            [
                (m[2, 1] - m[1, 2]) / s,
                0.25 * s,
                (m[0, 1] + m[1, 0]) / s,
                (m[0, 2] + m[2, 0]) / s,
            ],
            dtype=np.float64,
        )

    if m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2.0
        return np.array(
            [
                (m[0, 2] - m[2, 0]) / s,
                (m[0, 1] + m[1, 0]) / s,
                0.25 * s,
                (m[1, 2] + m[2, 1]) / s,
            ],
            dtype=np.float64,
        )

    s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2.0
    return np.array(
        [
            (m[1, 0] - m[0, 1]) / s,
            (m[0, 2] + m[2, 0]) / s,
            (m[1, 2] + m[2, 1]) / s,
            0.25 * s,
        ],
        dtype=np.float64,
    )


def quaternion_multiply(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    lw, lx, ly, lz = np.moveaxis(left, -1, 0)
    rw, rx, ry, rz = np.moveaxis(right, -1, 0)
    out = np.stack(
        [
            lw * rw - lx * rx - ly * ry - lz * rz,
            lw * rx + lx * rw + ly * rz - lz * ry,
            lw * ry - lx * rz + ly * rw + lz * rx,
            lw * rz + lx * ry - ly * rx + lz * rw,
        ],
        axis=-1,
    )
    norm = np.linalg.norm(out, axis=-1, keepdims=True)
    return out / np.clip(norm, EPS, None)


def _require_fields(cloud: SplatPly, names: list[str]) -> None:
    missing = [name for name in names if name not in cloud.data.dtype.names]
    if missing:
        raise ValueError(f"{cloud.path} is missing required fields: {missing}")


def apply_asset_transform(
    asset: SplatPly,
    placement: Placement,
    appearance: Appearance,
) -> SplatPly:
    if placement.scale <= 0.0:
        raise ValueError("Placement scale must be positive")

    _require_fields(asset, ["x", "y", "z"])

    transformed = asset.data.copy()
    xyz = np.column_stack(
        [
            transformed["x"].astype(np.float64),
            transformed["y"].astype(np.float64),
            transformed["z"].astype(np.float64),
        ]
    )
    rotation = rotation_matrix_xyz(placement.rotation_degrees)
    translation = np.asarray(placement.translation, dtype=np.float64)
    xyz = (xyz @ rotation.T) * placement.scale + translation
    transformed["x"] = xyz[:, 0]
    transformed["y"] = xyz[:, 1]
    transformed["z"] = xyz[:, 2]

    log_scale = float(np.log(placement.scale))
    for name in ("scale_0", "scale_1", "scale_2"):
        if name in transformed.dtype.names:
            transformed[name] = transformed[name] + log_scale

    rotation_fields = ["rot_0", "rot_1", "rot_2", "rot_3"]
    if all(name in transformed.dtype.names for name in rotation_fields):
        q_place = quaternion_from_matrix(rotation)
        q_place = q_place / np.linalg.norm(q_place)
        q_current = np.column_stack([transformed[name] for name in rotation_fields])
        q_new = quaternion_multiply(q_place[None, :], q_current.astype(np.float64))
        for index, name in enumerate(rotation_fields):
            transformed[name] = q_new[:, index]

    if "opacity" in transformed.dtype.names and appearance.opacity_multiplier != 1.0:
        alpha = sigmoid(transformed["opacity"].astype(np.float64))
        transformed["opacity"] = logit(alpha * appearance.opacity_multiplier)

    dc_fields = ["f_dc_0", "f_dc_1", "f_dc_2"]
    if all(name in transformed.dtype.names for name in dc_fields):
        mult = np.asarray(appearance.dc_color_multiplier, dtype=np.float64)
        bias = np.asarray(appearance.dc_color_bias, dtype=np.float64)
        for index, name in enumerate(dc_fields):
            transformed[name] = transformed[name] * mult[index] + bias[index]

    if appearance.sh_rest_multiplier != 1.0:
        for name in transformed.dtype.names or ():
            if name.startswith("f_rest_"):
                transformed[name] = transformed[name] * appearance.sh_rest_multiplier

    return SplatPly(
        path=asset.path,
        format_name=asset.format_name,
        version=asset.version,
        comments=asset.comments,
        properties=asset.properties,
        data=transformed,
    )


def merge_clouds(scene: SplatPly, asset: SplatPly) -> SplatPly:
    if scene.format_name != asset.format_name or scene.version != asset.version:
        raise ValueError("Scene and asset PLY files must use the same PLY format")
    if scene.properties != asset.properties:
        raise ValueError(
            "Scene and asset PLY properties differ. Train/export both assets with "
            "the same 3DGS implementation and SH degree."
        )
    merged = np.concatenate([scene.data, asset.data])
    return SplatPly(
        path=None,
        format_name=scene.format_name,
        version=scene.version,
        comments=scene.comments,
        properties=scene.properties,
        data=merged,
    )


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def placement_from_config(config: dict[str, Any]) -> Placement:
    raw = config.get("asset_transform", {})
    return Placement(
        scale=float(raw.get("scale", 1.0)),
        rotation_degrees=tuple(float(x) for x in raw.get("rotation_degrees", [0, 0, 0])),
        translation=tuple(float(x) for x in raw.get("translation", [0, 0, 0])),
    )


def appearance_from_config(config: dict[str, Any]) -> Appearance:
    raw = config.get("appearance", {})
    return Appearance(
        opacity_multiplier=float(raw.get("opacity_multiplier", 1.0)),
        dc_color_multiplier=tuple(
            float(x) for x in raw.get("dc_color_multiplier", [1, 1, 1])
        ),
        dc_color_bias=tuple(float(x) for x in raw.get("dc_color_bias", [0, 0, 0])),
        sh_rest_multiplier=float(raw.get("sh_rest_multiplier", 1.0)),
    )


def compose_from_config(config: dict[str, Any]) -> tuple[SplatPly, Path]:
    scene_path = Path(config["scene_ply"])
    asset_path = Path(config["asset_ply"])
    output_path = Path(config["output_ply"])

    scene = read_ply(scene_path)
    asset = read_ply(asset_path)
    transformed_asset = apply_asset_transform(
        asset,
        placement_from_config(config),
        appearance_from_config(config),
    )
    merged = merge_clouds(scene, transformed_asset)
    comments = [
        "Composed with tools/compose_splats.py",
        f"Scene: {scene_path}",
        f"Asset: {asset_path}",
    ]
    write_ply(merged, output_path, comments=comments)
    return merged, output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose two 3DGS point_cloud.ply files.")
    parser.add_argument("--config", required=True, help="Path to a placement JSON file.")
    args = parser.parse_args()

    config = load_config(args.config)
    merged, output_path = compose_from_config(config)
    print(f"Wrote {merged.vertex_count:,} gaussians to {output_path}")


if __name__ == "__main__":
    main()

