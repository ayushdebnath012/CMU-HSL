from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tools.compose_splats import compose_from_config, sigmoid
from tools.splat_ply import PlyProperty, SplatPly, read_ply, write_ply


FIELDS = [
    "x",
    "y",
    "z",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
    "opacity",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
]


def tiny_cloud(path: Path, xyz: tuple[float, float, float]) -> None:
    dtype = np.dtype([(field, "<f4") for field in FIELDS])
    data = np.zeros(1, dtype=dtype)
    data["x"] = xyz[0]
    data["y"] = xyz[1]
    data["z"] = xyz[2]
    data["rot_0"] = 1.0
    data["f_dc_0"] = 1.0
    data["f_dc_1"] = 1.0
    data["f_dc_2"] = 1.0

    properties = [PlyProperty("float", field) for field in FIELDS]
    cloud = SplatPly(
        path=None,
        format_name="binary_little_endian",
        version="1.0",
        comments=[],
        properties=properties,
        data=data,
    )
    write_ply(cloud, path)


def test_compose_applies_transform_and_appearance(tmp_path: Path) -> None:
    scene_path = tmp_path / "scene.ply"
    asset_path = tmp_path / "asset.ply"
    output_path = tmp_path / "merged.ply"
    tiny_cloud(scene_path, (0.0, 0.0, 0.0))
    tiny_cloud(asset_path, (1.0, 0.0, 0.0))

    config = {
        "scene_ply": str(scene_path),
        "asset_ply": str(asset_path),
        "output_ply": str(output_path),
        "asset_transform": {
            "scale": 2.0,
            "rotation_degrees": [0.0, 0.0, 90.0],
            "translation": [10.0, 0.0, 0.0],
        },
        "appearance": {
            "opacity_multiplier": 0.5,
            "dc_color_multiplier": [2.0, 1.0, 1.0],
            "dc_color_bias": [0.0, 0.0, 0.0],
            "sh_rest_multiplier": 1.0,
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    merged, _ = compose_from_config(config)
    assert merged.vertex_count == 2

    out = read_ply(output_path)
    asset = out.data[1]
    assert np.allclose([asset["x"], asset["y"], asset["z"]], [10.0, 2.0, 0.0])
    assert np.allclose(
        [asset["scale_0"], asset["scale_1"], asset["scale_2"]],
        [np.log(2.0), np.log(2.0), np.log(2.0)],
    )
    assert np.allclose(
        [asset["rot_0"], asset["rot_1"], asset["rot_2"], asset["rot_3"]],
        [np.sqrt(0.5), 0.0, 0.0, np.sqrt(0.5)],
    )
    assert np.allclose(sigmoid(np.array([asset["opacity"]])), [0.25], atol=1e-5)
    assert np.allclose([asset["f_dc_0"], asset["f_dc_1"], asset["f_dc_2"]], [2.0, 1.0, 1.0])

