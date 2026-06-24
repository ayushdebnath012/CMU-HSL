# Training On Google Colab

Use this when your laptop cannot run 3DGS training locally. The workflow is:

1. Train the two 3DGS models in Colab.
2. Save `outputs/` to Google Drive.
3. Compose the two trained `point_cloud.ply` files with this repo's tools.
4. Download the composed model and rendered images.

Colab setup changes often, so treat this as a practical baseline. If a CUDA extension fails to compile, restart the runtime and run the setup cells again.

## One-Command Version

Put `nerf_synthetic.zip` in:

```text
/content/drive/MyDrive/HSL_3DGS/nerf_synthetic.zip
```

Then run this in Colab:

```bash
git clone https://github.com/ayushdebnath012/CMU-HSL.git /content/CMU-HSL
bash /content/CMU-HSL/scripts/colab_run_all.sh smoke
```

If the smoke test works, run the full training:

```bash
bash /content/CMU-HSL/scripts/colab_run_all.sh full
```

Optional: choose a different NeRF-Synthetic object if it exists in your zip:

```bash
ASSET_NAME=lego bash /content/CMU-HSL/scripts/colab_run_all.sh smoke
```

## 0. Runtime

In Colab, choose:

```text
Runtime > Change runtime type > GPU
```

An A100/L4/V100 GPU is much better than a T4. Bicycle can be heavy, so start with a 7k-iteration smoke test before running the full 30k training.

## 1. Mount Drive And Set Paths

```python
from google.colab import drive
drive.mount("/content/drive")

PROJECT = "/content/CMU-HSL"
DRIVE_ROOT = "/content/drive/MyDrive/HSL_3DGS"
DATA_ROOT = "/content/data"
OUT_ROOT = "/content/outputs"
```

If your project is already on GitHub:

```bash
git clone YOUR_PRIVATE_REPO_URL /content/CMU-HSL
cd /content/CMU-HSL
pip install -q -r requirements.txt
```

If you have not pushed it yet, zip this folder and upload it to Drive, then:

```bash
unzip -q "/content/drive/MyDrive/HSL_3DGS/CMU-HSL.zip" -d /content
cd /content/CMU-HSL
pip install -q -r requirements.txt
```

## 2. Clone And Build Official 3DGS

```bash
cd /content
git clone https://github.com/graphdeco-inria/gaussian-splatting --recursive
cd /content/gaussian-splatting

pip install -q plyfile tqdm opencv-python joblib
pip install -q submodules/diff-gaussian-rasterization
pip install -q submodules/simple-knn
```

Quick CUDA check:

```python
import torch
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

## 3. Download / Prepare Data

Mip-NeRF 360 Bicycle:

```bash
mkdir -p /content/data/360_v2
wget -c http://storage.googleapis.com/gresearch/refraw360/360_v2.zip -O /content/data/360_v2.zip
unzip -q /content/data/360_v2.zip -d /content/data/360_v2
ls /content/data/360_v2/bicycle
```

NeRF-Synthetic:

Download `nerf_synthetic.zip` from the official NeRF data link and place it in:

```text
/content/drive/MyDrive/HSL_3DGS/nerf_synthetic.zip
```

Then extract it:

```bash
mkdir -p /content/data
unzip -q "/content/drive/MyDrive/HSL_3DGS/nerf_synthetic.zip" -d /content/data
ls /content/data/nerf_synthetic/chair
```

The object folder should contain files such as `transforms_train.json` and `transforms_test.json`.

## 4. Train Smoke Tests

Run short training first so you know the CUDA extensions and paths are correct.

```bash
cd /content/gaussian-splatting

python train.py \
  -s /content/data/360_v2/bicycle \
  -m /content/outputs/bicycle_7k \
  --eval \
  -i images_4 \
  --data_device cpu \
  --iterations 7000 \
  --save_iterations 7000

python train.py \
  -s /content/data/nerf_synthetic/chair \
  -m /content/outputs/chair_7k \
  --eval \
  -w \
  --iterations 7000 \
  --save_iterations 7000
```

If these finish, copy the smoke-test results to Drive:

```bash
mkdir -p "/content/drive/MyDrive/HSL_3DGS/outputs"
cp -r /content/outputs/bicycle_7k "/content/drive/MyDrive/HSL_3DGS/outputs/"
cp -r /content/outputs/chair_7k "/content/drive/MyDrive/HSL_3DGS/outputs/"
```

## 5. Full Training

Run full training when the smoke test works:

```bash
cd /content/gaussian-splatting

python train.py \
  -s /content/data/360_v2/bicycle \
  -m /content/outputs/bicycle \
  --eval \
  -i images_4 \
  --data_device cpu \
  --iterations 30000 \
  --save_iterations 7000 30000

python train.py \
  -s /content/data/nerf_synthetic/chair \
  -m /content/outputs/chair \
  --eval \
  -w \
  --iterations 30000 \
  --save_iterations 7000 30000
```

Save the trained models:

```bash
mkdir -p "/content/drive/MyDrive/HSL_3DGS/outputs"
cp -r /content/outputs/bicycle "/content/drive/MyDrive/HSL_3DGS/outputs/"
cp -r /content/outputs/chair "/content/drive/MyDrive/HSL_3DGS/outputs/"
```

## 6. Inspect Scale

```bash
cd /content/CMU-HSL

python tools/scene_stats.py /content/outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply --pretty
python tools/scene_stats.py /content/outputs/chair/point_cloud/iteration_30000/point_cloud.ply --pretty
```

Use those bounds to update:

```text
configs/bicycle_chair.json
```

At first, only change:

```json
"scale": 0.15,
"translation": [0.0, 0.0, 0.0],
"rotation_degrees": [0.0, 0.0, 0.0]
```

## 7. Compose The Splats

For a 7k smoke test:

```bash
cd /content/CMU-HSL

python tools/compose_splats.py --config <(python - <<'PY'
import json
config = json.load(open("configs/bicycle_chair.json"))
config["scene_ply"] = "/content/outputs/bicycle_7k/point_cloud/iteration_7000/point_cloud.ply"
config["asset_ply"] = "/content/outputs/chair_7k/point_cloud/iteration_7000/point_cloud.ply"
config["output_ply"] = "/content/outputs/composed_bicycle_chair_7k/point_cloud/iteration_7000/point_cloud.ply"
print(json.dumps(config))
PY
)
```

For full 30k:

```bash
cd /content/CMU-HSL

python tools/compose_splats.py --config <(python - <<'PY'
import json
config = json.load(open("configs/bicycle_chair.json"))
config["scene_ply"] = "/content/outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply"
config["asset_ply"] = "/content/outputs/chair/point_cloud/iteration_30000/point_cloud.ply"
config["output_ply"] = "/content/outputs/composed_bicycle_chair/point_cloud/iteration_30000/point_cloud.ply"
print(json.dumps(config))
PY
)
```

Create a quick preview:

```bash
python tools/preview_bounds.py \
  --scene /content/outputs/bicycle/point_cloud/iteration_30000/point_cloud.ply \
  --asset /content/outputs/composed_bicycle_chair/point_cloud/iteration_30000/point_cloud.ply \
  --out /content/outputs/composed_bounds.png
```

Save the composed result:

```bash
cp -r /content/outputs/composed_bicycle_chair "/content/drive/MyDrive/HSL_3DGS/outputs/"
cp /content/outputs/composed_bounds.png "/content/drive/MyDrive/HSL_3DGS/outputs/"
```

## 8. Render

The easiest render path is to copy the scene model directory and replace its `point_cloud.ply` with the composed one. This preserves the Bicycle cameras/config files.

```bash
cp -r /content/outputs/bicycle /content/outputs/composed_model
mkdir -p /content/outputs/composed_model/point_cloud/iteration_30000
cp /content/outputs/composed_bicycle_chair/point_cloud/iteration_30000/point_cloud.ply \
   /content/outputs/composed_model/point_cloud/iteration_30000/point_cloud.ply

cd /content/gaussian-splatting
python render.py -m /content/outputs/composed_model
```

Save renders:

```bash
cp -r /content/outputs/composed_model "/content/drive/MyDrive/HSL_3DGS/outputs/"
```

## Notes For The Final Submission

- Keep the trained models out of Git unless the repository size is acceptable.
- Push source code, configs, docs, and the presentation.
- Put large trained outputs in Drive or GitHub Releases if needed.
- In the technical call, be explicit that cross-dataset scale is a similarity-transform ambiguity, then show the bounding-box and visual-anchor procedure you used.
