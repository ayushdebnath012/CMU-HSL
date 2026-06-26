from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from tools.compose_splats import (
        appearance_from_config,
        apply_asset_transform,
        load_config,
        placement_from_config,
    )
    from tools.splat_ply import read_ply
except ModuleNotFoundError:
    from compose_splats import (
        appearance_from_config,
        apply_asset_transform,
        load_config,
        placement_from_config,
    )
    from splat_ply import read_ply


def xyz_from_cloud(cloud) -> np.ndarray:
    return np.column_stack([cloud.data["x"], cloud.data["y"], cloud.data["z"]]).astype(
        np.float64
    )


def sample(points: np.ndarray, limit: int, seed: int) -> np.ndarray:
    if points.shape[0] <= limit:
        return points
    rng = np.random.default_rng(seed)
    indices = rng.choice(points.shape[0], size=limit, replace=False)
    return points[indices]


def set_equal_axes(ax, points: np.ndarray) -> None:
    center = (points.min(axis=0) + points.max(axis=0)) * 0.5
    radius = float((points.max(axis=0) - points.min(axis=0)).max() * 0.55)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview Bicycle scene plus transformed foreground asset."
    )
    parser.add_argument("--config", required=True, help="Placement config JSON")
    parser.add_argument("--out", default="outputs/previews/placement.png")
    parser.add_argument("--sample", type=int, default=60000)
    args = parser.parse_args()

    config = load_config(args.config)
    scene = read_ply(config["scene_ply"])
    asset = read_ply(config["asset_ply"])
    transformed_asset = apply_asset_transform(
        asset,
        placement_from_config(config),
        appearance_from_config(config),
    )

    scene_xyz = sample(xyz_from_cloud(scene), args.sample, 7)
    asset_xyz = sample(xyz_from_cloud(transformed_asset), args.sample, 11)
    combined = np.vstack([scene_xyz, asset_xyz])

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(
        scene_xyz[:, 0],
        scene_xyz[:, 1],
        scene_xyz[:, 2],
        s=0.15,
        c="#777777",
        alpha=0.22,
        label="Bicycle scene",
    )
    ax.scatter(
        asset_xyz[:, 0],
        asset_xyz[:, 1],
        asset_xyz[:, 2],
        s=0.55,
        c="#d14b3f",
        alpha=0.8,
        label="Transformed asset",
    )
    set_equal_axes(ax, combined)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title("3DGS placement preview")
    ax.legend(loc="upper right")
    ax.view_init(elev=24, azim=-55)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

