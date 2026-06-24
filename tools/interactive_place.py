from __future__ import annotations

import argparse
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    from tools.compose_splats import compose_from_config
except ModuleNotFoundError:
    from compose_splats import compose_from_config


SLIDER_DEFS = [
    ("scale", "Scale", 0.01, 2.0, 0.01),
    ("tx", "Translate X", -20.0, 20.0, 0.01),
    ("ty", "Translate Y", -20.0, 20.0, 0.01),
    ("tz", "Translate Z", -20.0, 20.0, 0.01),
    ("rx", "Rotate X", -180.0, 180.0, 1.0),
    ("ry", "Rotate Y", -180.0, 180.0, 1.0),
    ("rz", "Rotate Z", -180.0, 180.0, 1.0),
    ("opacity", "Opacity Multiplier", 0.1, 2.0, 0.01),
]


def _default_config() -> dict:
    return {
        "scene_ply": "outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply",
        "asset_ply": "outputs/chair/point_cloud/iteration_30000/point_cloud.ply",
        "output_ply": "outputs/composed_bicycle_chair/point_cloud/iteration_30000/point_cloud.ply",
        "asset_transform": {
            "scale": 0.15,
            "rotation_degrees": [0.0, 0.0, 0.0],
            "translation": [0.0, 0.0, 0.0],
        },
        "appearance": {
            "opacity_multiplier": 1.0,
            "dc_color_multiplier": [1.0, 1.0, 1.0],
            "dc_color_bias": [0.0, 0.0, 0.0],
            "sh_rest_multiplier": 1.0,
        },
    }


def load_config(path: Path) -> dict:
    if not path.exists():
        return _default_config()
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def values_from_config(config: dict) -> dict[str, float]:
    transform = config.setdefault("asset_transform", {})
    appearance = config.setdefault("appearance", {})
    rotation = transform.setdefault("rotation_degrees", [0.0, 0.0, 0.0])
    translation = transform.setdefault("translation", [0.0, 0.0, 0.0])
    return {
        "scale": float(transform.get("scale", 1.0)),
        "tx": float(translation[0]),
        "ty": float(translation[1]),
        "tz": float(translation[2]),
        "rx": float(rotation[0]),
        "ry": float(rotation[1]),
        "rz": float(rotation[2]),
        "opacity": float(appearance.get("opacity_multiplier", 1.0)),
    }


def apply_values_to_config(config: dict, values: dict[str, float]) -> None:
    config.setdefault("asset_transform", {})
    config.setdefault("appearance", {})
    config["asset_transform"]["scale"] = float(values["scale"])
    config["asset_transform"]["translation"] = [
        float(values["tx"]),
        float(values["ty"]),
        float(values["tz"]),
    ]
    config["asset_transform"]["rotation_degrees"] = [
        float(values["rx"]),
        float(values["ry"]),
        float(values["rz"]),
    ]
    config["appearance"]["opacity_multiplier"] = float(values["opacity"])


class PlacementApp:
    def __init__(self, root: tk.Tk, config_path: Path):
        self.root = root
        self.config_path = config_path
        self.config = load_config(config_path)
        self.vars: dict[str, tk.DoubleVar] = {}

        root.title("3DGS Asset Placement")
        root.geometry("720x520")

        title = tk.Label(root, text="3DGS Asset Placement", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", padx=16, pady=(16, 4))

        subtitle = tk.Label(
            root,
            text="Adjust the foreground transform, then write a composed point_cloud.ply.",
            font=("Segoe UI", 10),
        )
        subtitle.pack(anchor="w", padx=16, pady=(0, 12))

        paths = tk.Label(
            root,
            text=(
                f"Config: {config_path}\n"
                f"Scene: {self.config.get('scene_ply')}\n"
                f"Asset: {self.config.get('asset_ply')}\n"
                f"Output: {self.config.get('output_ply')}"
            ),
            justify="left",
            anchor="w",
        )
        paths.pack(fill="x", padx=16, pady=(0, 8))

        values = values_from_config(self.config)
        frame = tk.Frame(root)
        frame.pack(fill="both", expand=True, padx=16, pady=8)

        for row, (key, label, minimum, maximum, step) in enumerate(SLIDER_DEFS):
            tk.Label(frame, text=label, width=18, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            var = tk.DoubleVar(value=values[key])
            self.vars[key] = var
            slider = tk.Scale(
                frame,
                from_=minimum,
                to=maximum,
                resolution=step,
                orient="horizontal",
                variable=var,
                length=420,
            )
            slider.grid(row=row, column=1, sticky="ew", pady=4)
            entry = tk.Entry(frame, textvariable=var, width=10)
            entry.grid(row=row, column=2, sticky="e", padx=(8, 0))

        frame.columnconfigure(1, weight=1)

        button_frame = tk.Frame(root)
        button_frame.pack(fill="x", padx=16, pady=(8, 16))
        tk.Button(button_frame, text="Save Config", command=self.save).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(button_frame, text="Compose PLY", command=self.compose).pack(
            side="left", padx=(0, 8)
        )
        tk.Button(button_frame, text="Save + Compose", command=self.save_and_compose).pack(
            side="left"
        )

    def current_values(self) -> dict[str, float]:
        return {key: var.get() for key, var in self.vars.items()}

    def save(self) -> None:
        apply_values_to_config(self.config, self.current_values())
        save_config(self.config_path, self.config)
        messagebox.showinfo("Saved", f"Wrote {self.config_path}")

    def compose(self) -> None:
        apply_values_to_config(self.config, self.current_values())
        try:
            merged, output_path = compose_from_config(self.config)
        except Exception as exc:
            messagebox.showerror("Compose failed", str(exc))
            return
        messagebox.showinfo(
            "Composed",
            f"Wrote {merged.vertex_count:,} Gaussians to:\n{output_path}",
        )

    def save_and_compose(self) -> None:
        apply_values_to_config(self.config, self.current_values())
        save_config(self.config_path, self.config)
        self.compose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Small Tk UI for 3DGS asset placement.")
    parser.add_argument(
        "--config",
        default="configs/bicycle_chair.json",
        help="Placement config to load and update.",
    )
    args = parser.parse_args()

    root = tk.Tk()
    PlacementApp(root, Path(args.config))
    root.mainloop()


if __name__ == "__main__":
    main()

