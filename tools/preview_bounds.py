from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from tools.splat_ply import read_ply
except ModuleNotFoundError:
    from splat_ply import read_ply


def sample_xyz(path: Path, limit: int) -> np.ndarray:
    cloud = read_ply(path)
    xyz = np.column_stack([cloud.data["x"], cloud.data["y"], cloud.data["z"]]).astype(
        np.float64
    )
    if xyz.shape[0] <= limit:
        return xyz
    rng = np.random.default_rng(7)
    indices = rng.choice(xyz.shape[0], size=limit, replace=False)
    return xyz[indices]


def set_equal_axes(ax, points: np.ndarray) -> None:
    center = (points.min(axis=0) + points.max(axis=0)) * 0.5
    radius = float((points.max(axis=0) - points.min(axis=0)).max() * 0.55)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a quick point preview of splat bounds.")
    parser.add_argument("--scene", required=True, help="Scene point_cloud.ply")
    parser.add_argument("--asset", help="Asset or composed point_cloud.ply")
    parser.add_argument(
        "--out", default="outputs/previews/bounds.png", help="Output PNG path"
    )
    parser.add_argument("--sample", type=int, default=60000)
    args = parser.parse_args()

    scene = sample_xyz(Path(args.scene), args.sample)
    all_points = [scene]

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(scene[:, 0], scene[:, 1], scene[:, 2], s=0.15, c="#777777", alpha=0.35)

    if args.asset:
        asset = sample_xyz(Path(args.asset), args.sample)
        all_points.append(asset)
        ax.scatter(asset[:, 0], asset[:, 1], asset[:, 2], s=0.3, c="#d14b3f", alpha=0.7)

    combined = np.vstack(all_points)
    set_equal_axes(ax, combined)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title("3DGS bounds preview")
    ax.view_init(elev=24, azim=-55)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

