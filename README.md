# Human Sensing Lab Technical Assessment

This repository contains a reproducible baseline for composing two 3D Gaussian Splatting reconstructions:

- a background scene trained on the Mip-NeRF 360 `bicycle` scene
- a foreground object trained on one NeRF-Synthetic object, defaulting to `chair`
- a splat-level composer that transforms the foreground Gaussians into the scene coordinate frame and writes one merged `point_cloud.ply`

The local machine used to create this scaffold did not expose `conda` or `nvidia-smi`, so full 3DGS training was not run here. The code and scripts are intended to run on a CUDA-capable machine with the official Graphdeco 3DGS environment.

## Repository Layout

```text
configs/                 Placement JSON files
docs/                    Method notes and slide outline
scripts/                 PowerShell setup, train, compose, render commands
tools/                   PLY reader, composer, stats, and placement UI
presentation/            3-slide presentation draft
data/                    Local datasets, ignored by Git
outputs/                 Trained/composed models, ignored by Git
```

## Setup

Install the lightweight local tools:

```powershell
python -m pip install -r requirements.txt
```

Clone the official 3DGS implementation:

```powershell
.\scripts\setup_3dgs.ps1
```

On the GPU machine, activate the official environment before training:

```powershell
conda activate gaussian_splatting
```

The official 3DGS optimizer requires a CUDA GPU, a compatible C++ compiler, and a CUDA SDK/PyTorch setup that can compile the rasterizer extensions.

For Google Colab training, use the one-shot runner:

```bash
git clone https://github.com/ayushdebnath012/CMU-HSL.git /content/CMU-HSL
bash /content/CMU-HSL/scripts/colab_run_all.sh smoke
```

Then run `bash /content/CMU-HSL/scripts/colab_run_all.sh full` for the full 30k training. More details are in [docs/colab.md](docs/colab.md).

## Data

Download Mip-NeRF 360:

```powershell
.\scripts\download_mipnerf360.ps1
```

This is a large archive, about 12.5 GB. The expected Bicycle path is:

```text
data/360_v2/bicycle
```

Download NeRF-Synthetic from the official NeRF data link and place the desired object at:

```text
data/nerf_synthetic/chair
```

The object folder should contain `transforms_train.json`, `transforms_test.json`, and the corresponding image folders/files.

## Train

Train the Bicycle scene:

```powershell
.\scripts\train_bicycle.ps1
```

Train the foreground object:

```powershell
.\scripts\train_asset.ps1 -Dataset data/nerf_synthetic/chair -Output outputs/chair
```

The expected trained model PLY files are:

```text
outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply
outputs/chair/point_cloud/iteration_30000/point_cloud.ply
```

## Inspect Scale

Print scene/object bounds:

```powershell
python tools/scene_stats.py outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply --pretty
python tools/scene_stats.py outputs/chair/point_cloud/iteration_30000/point_cloud.ply --pretty
```

The assignment asks us to reason about camera calibration and relative scale. The key point is that each dataset is internally calibrated, but the Bicycle reconstruction and the synthetic object do not share a guaranteed metric unit. The baseline therefore uses bounding boxes and visual anchors, then refines scale interactively.

## Compose

Edit `configs/bicycle_chair.json` or open the small placement UI:

```powershell
python tools/interactive_place.py --config configs/bicycle_chair.json
```

Generate a composed model directory:

```powershell
.\scripts\compose_bicycle_chair.ps1
```

Render the composed model through the official renderer:

```powershell
.\scripts\render_composed.ps1
```

You can also generate a quick static bounds preview:

```powershell
python tools/preview_bounds.py `
  --scene outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply `
  --asset outputs/composed_bicycle_chair/point_cloud/iteration_30000/point_cloud.ply `
  --out outputs/previews/composed_bounds.png
```

## Composition Method

For each foreground Gaussian center:

```text
p_scene = scale * R * p_object + t
```

The composer also updates the 3DGS-specific fields:

- `scale_0`, `scale_1`, `scale_2`: add `log(scale)` because Graphdeco stores Gaussian scale in log space
- `rot_0`, `rot_1`, `rot_2`, `rot_3`: left-multiply by the placement quaternion
- `opacity`: convert raw opacity through sigmoid, multiply alpha, then convert back with logit
- `f_dc_*` and `f_rest_*`: optional simple color/exposure adjustments

The output is a single merged `point_cloud.ply`. Rendering one merged splat set is the baseline occlusion strategy because the 3DGS rasterizer can depth-sort and alpha-composite all Gaussians together.

## References

- Official 3DGS implementation: https://github.com/graphdeco-inria/gaussian-splatting
- 3DGS project page: https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
- Mip-NeRF 360 dataset page: https://jonbarron.info/mipnerf360/
- NeRF project/data page: https://www.matthewtancik.com/nerf
