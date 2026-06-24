from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    from tools.splat_ply import read_ply
except ModuleNotFoundError:
    from splat_ply import read_ply


def stats_for_ply(path: str | Path) -> dict:
    cloud = read_ply(path)
    names = cloud.data.dtype.names or ()
    for required in ("x", "y", "z"):
        if required not in names:
            raise ValueError(f"{path} is missing field {required}")

    xyz = np.column_stack([cloud.data["x"], cloud.data["y"], cloud.data["z"]]).astype(
        np.float64
    )
    bbox_min = xyz.min(axis=0)
    bbox_max = xyz.max(axis=0)
    extent = bbox_max - bbox_min
    center = (bbox_min + bbox_max) * 0.5
    percentiles = np.percentile(xyz[:, 2], [1, 5, 50, 95, 99])

    return {
        "path": str(path),
        "gaussians": cloud.vertex_count,
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "extent": extent.tolist(),
        "center": center.tolist(),
        "diagonal": float(np.linalg.norm(extent)),
        "z_percentiles": {
            "p01": float(percentiles[0]),
            "p05": float(percentiles[1]),
            "p50": float(percentiles[2]),
            "p95": float(percentiles[3]),
            "p99": float(percentiles[4]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Print bounds for a 3DGS PLY file.")
    parser.add_argument("ply", help="Path to point_cloud.ply")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    result = stats_for_ply(args.ply)
    print(json.dumps(result, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()

