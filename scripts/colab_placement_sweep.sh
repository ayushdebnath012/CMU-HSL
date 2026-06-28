#!/usr/bin/env bash
set -euo pipefail

# Colab version of the placement sweep. Reuses existing t4full trained models and
# writes a contact sheet to Google Drive outputs.

PROJECT_DIR="${PROJECT_DIR:-/content/CMU-HSL}"
MODE="${MODE:-t4full}"
LOG_DIR="${LOG_DIR:-/content}"
MONTAGE_PATH="${MONTAGE_PATH:-/content/drive/MyDrive/HSL_3DGS/outputs/placement_sweep_montage.png}"

cd "$PROJECT_DIR"
git pull --ff-only || true

run_variant() {
  local tag="$1"
  local scale="$2"
  local tx="$3"
  local ty="$4"
  local tz="$5"
  local opacity="$6"

  echo "=== placement variant: $tag ==="
  ASSET_SCALE="$scale" \
  ASSET_TX="$tx" \
  ASSET_TY="$ty" \
  ASSET_TZ="$tz" \
  ASSET_OPACITY="$opacity" \
  RUN_TAG="$tag" \
  LOG_FILE="$LOG_DIR/hsl_place_${tag}.log" \
  bash scripts/colab_run_all.sh "$MODE"
}

run_variant "tiny_soft"      0.025  0    0    0     0.30
run_variant "soft_xleft"     0.025 -3    0    0     0.30
run_variant "soft_xright"    0.025  3    0    0     0.30
run_variant "soft_yplus"     0.025  0    3    0     0.30
run_variant "soft_yminus"    0.025  0   -3    0     0.30
run_variant "small_visible"  0.035  0    0    0     0.35

python - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw
import glob
import os

montage_path = Path(os.environ.get("MONTAGE_PATH", "/content/drive/MyDrive/HSL_3DGS/outputs/placement_sweep_montage.png"))
tags = [
    "tiny_soft",
    "soft_xleft",
    "soft_xright",
    "soft_yplus",
    "soft_yminus",
    "small_visible",
]

tiles = []
for tag in tags:
    pattern = f"/content/outputs/render_composed_bicycle_chair_t4full_{tag}/test/ours_30000/renders/*.png"
    imgs = sorted(glob.glob(pattern))
    if not imgs:
        pattern = f"/content/outputs/render_composed_bicycle_chair_t4full_{tag}/**/renders/*.png"
        imgs = sorted(glob.glob(pattern, recursive=True))
    if not imgs:
        print(f"No render found for {tag}")
        continue
    img = Image.open(imgs[0]).convert("RGB")
    img.thumbnail((520, 330))
    tile = Image.new("RGB", (560, 390), "white")
    tile.paste(img, ((560 - img.width) // 2, 20))
    draw = ImageDraw.Draw(tile)
    draw.text((20, 355), tag, fill=(20, 20, 20))
    tiles.append(tile)

if not tiles:
    raise SystemExit("No placement renders found; cannot build montage")

cols = 2
rows = (len(tiles) + cols - 1) // cols
montage = Image.new("RGB", (cols * 560, rows * 390), "white")
for i, tile in enumerate(tiles):
    x = (i % cols) * 560
    y = (i // cols) * 390
    montage.paste(tile, (x, y))

montage_path.parent.mkdir(parents=True, exist_ok=True)
montage.save(montage_path)
print(f"Wrote {montage_path}")
PY

echo "Placement sweep complete."
echo "Montage: $MONTAGE_PATH"
