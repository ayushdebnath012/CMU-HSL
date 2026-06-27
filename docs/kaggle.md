# Training On Kaggle

Use this if Colab Drive is unstable or you want Kaggle GPU runtime.

## Kaggle Settings

In the Kaggle notebook sidebar:

```text
Settings > Accelerator > GPU
Settings > Internet > On
```

Kaggle input folders are read-only under `/kaggle/input`. Outputs should be written to `/kaggle/working`.

## NeRF-Synthetic Input

The runner can download Bicycle automatically. For NeRF-Synthetic, the safest route is:

1. Download the NeRF synthetic dataset from https://www.matthewtancik.com/nerf.
2. Rename it to `nerf_synthetic.zip`.
3. Upload it as a private Kaggle Dataset.
4. In your notebook, click **Add Input** and attach that dataset.

The script will search `/kaggle/input` for `nerf_synthetic.zip` or an extracted `nerf_synthetic/chair` folder.

## One Cell

Run this in Kaggle:

```bash
!git clone https://github.com/ayushdebnath012/CMU-HSL.git /kaggle/working/CMU-HSL || true
!cd /kaggle/working/CMU-HSL && git pull
!LOG_FILE=/kaggle/working/hsl_kaggle_t4full.log bash /kaggle/working/CMU-HSL/scripts/kaggle_run_all.sh t4full
```

The `t4full` mode runs 30k iterations with T4-safer settings:

```text
images_8
--test_iterations -1
--densify_until_iter 12000
--densify_grad_threshold 0.001
--densification_interval 300
```

## View Renders

```python
from PIL import Image
import glob, matplotlib.pyplot as plt

imgs = sorted(glob.glob("/kaggle/working/hsl_outputs/render_composed_bicycle_chair_t4full/**/renders/*.png", recursive=True))
print(len(imgs))
print(imgs[:5])

img = Image.open(imgs[0])
plt.figure(figsize=(12, 7))
plt.imshow(img)
plt.axis("off")
```

## Placement Variant

After training once, rerun only composition/render with placement overrides:

```bash
!cd /kaggle/working/CMU-HSL && \
  ASSET_SCALE=0.045 \
  ASSET_TZ=-4 \
  ASSET_OPACITY=0.45 \
  RUN_TAG=small_down4 \
  LOG_FILE=/kaggle/working/hsl_small_down4.log \
  bash scripts/kaggle_run_all.sh t4full
```

## Outputs

Important output folders:

```text
/kaggle/working/hsl_outputs/bicycle_t4full
/kaggle/working/hsl_outputs/chair_t4full
/kaggle/working/hsl_outputs/composed_bicycle_chair_t4full
/kaggle/working/hsl_outputs/render_composed_bicycle_chair_t4full
```

You can download them from the Kaggle notebook output panel after the run completes.

