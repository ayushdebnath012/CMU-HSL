#!/usr/bin/env bash
set -euo pipefail

if [[ "${DEBUG:-0}" == "1" ]]; then
  set -x
fi

LOG_FILE="${LOG_FILE:-/content/hsl_colab_run.log}"
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'status=$?; echo; echo "ERROR: colab_run_all.sh failed at line $LINENO with exit code $status"; echo "Inspect log with: tail -n 160 $LOG_FILE"; exit $status' ERR

# One-shot Colab runner for the HSL 3DGS composition assignment.
#
# Usage in Colab:
#   !git clone https://github.com/ayushdebnath012/CMU-HSL.git /content/CMU-HSL
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh lite
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh smoke
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh t4full
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh full
#
# Before running, put nerf_synthetic.zip in:
#   /content/drive/MyDrive/HSL_3DGS/nerf_synthetic.zip

MODE="${1:-lite}"                  # lite, smoke, t4full, or full
ASSET_NAME="${ASSET_NAME:-chair}"
PROJECT_REPO="${PROJECT_REPO:-https://github.com/ayushdebnath012/CMU-HSL.git}"
PROJECT_DIR="${PROJECT_DIR:-/content/CMU-HSL}"
GS_DIR="${GS_DIR:-/content/gaussian-splatting}"
DATA_DIR="${DATA_DIR:-/content/data}"
OUT_DIR="${OUT_DIR:-/content/outputs}"
DRIVE_ROOT="${DRIVE_ROOT:-/content/drive/MyDrive/HSL_3DGS}"
NERF_ZIP="${NERF_ZIP:-$DRIVE_ROOT/nerf_synthetic.zip}"
NERF_DOWNLOAD_ZIP="${NERF_DOWNLOAD_ZIP:-$DATA_DIR/nerf_synthetic.zip}"
# Common public Google Drive file ID for the original NeRF Blender synthetic zip.
# Google occasionally rate-limits or changes Drive access behavior, so the script
# falls back to a user-uploaded zip if this download fails.
NERF_SYNTHETIC_GDRIVE_ID="${NERF_SYNTHETIC_GDRIVE_ID:-18JxhpWD-4ZmuFKLzKlAw-w5PpzZxXOcG}"

if [[ "$MODE" == "full" ]]; then
  ITERATIONS="${ITERATIONS_OVERRIDE:-30000}"
  BICYCLE_MODEL="$OUT_DIR/bicycle"
  ASSET_MODEL="$OUT_DIR/$ASSET_NAME"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}"
  BICYCLE_IMAGES="${BICYCLE_IMAGES:-images_4}"
  TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---test_iterations -1}"
elif [[ "$MODE" == "smoke" ]]; then
  ITERATIONS="${ITERATIONS_OVERRIDE:-7000}"
  BICYCLE_MODEL="$OUT_DIR/bicycle_7k"
  ASSET_MODEL="$OUT_DIR/${ASSET_NAME}_7k"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}_7k"
  BICYCLE_IMAGES="${BICYCLE_IMAGES:-images_8}"
  TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---test_iterations -1 --densify_until_iter 3000 --densify_grad_threshold 0.0005 --densification_interval 200}"
elif [[ "$MODE" == "t4full" ]]; then
  ITERATIONS="${ITERATIONS_OVERRIDE:-30000}"
  BICYCLE_MODEL="$OUT_DIR/bicycle_t4full"
  ASSET_MODEL="$OUT_DIR/${ASSET_NAME}_t4full"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}_t4full"
  BICYCLE_IMAGES="${BICYCLE_IMAGES:-images_8}"
  TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---test_iterations -1 --densify_until_iter 12000 --densify_grad_threshold 0.001 --densification_interval 300}"
else
  ITERATIONS="${ITERATIONS_OVERRIDE:-3000}"
  BICYCLE_MODEL="$OUT_DIR/bicycle_lite"
  ASSET_MODEL="$OUT_DIR/${ASSET_NAME}_lite"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}_lite"
  BICYCLE_IMAGES="${BICYCLE_IMAGES:-images_8}"
  TRAIN_EXTRA_ARGS="${TRAIN_EXTRA_ARGS:---test_iterations -1 --densify_until_iter 1000 --densify_grad_threshold 0.001 --densification_interval 300}"
fi

BICYCLE_DATA="$DATA_DIR/360_v2/bicycle"
ASSET_DATA="$DATA_DIR/nerf_synthetic/$ASSET_NAME"

echo "Mode: $MODE"
echo "Iterations: $ITERATIONS"
echo "Asset: $ASSET_NAME"
echo "Bicycle image folder: $BICYCLE_IMAGES"
echo "Extra train args: $TRAIN_EXTRA_ARGS"
echo "Log file: $LOG_FILE"

if [[ ! -d "/content/drive/MyDrive" ]]; then
  echo "Google Drive is not mounted."
  echo "Mount Drive in a Python Colab cell first:"
  echo "  from google.colab import drive"
  echo "  drive.mount('/content/drive')"
  echo "Then rerun this script."
  echo "Set ALLOW_NO_DRIVE=1 only if you intentionally do not want Drive output copies."
  if [[ "${ALLOW_NO_DRIVE:-0}" != "1" ]]; then
    exit 1
  fi
fi

python - <<'PY'
import torch
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    raise SystemExit("No CUDA GPU available. In Colab, set Runtime > Change runtime type > GPU.")
PY

mkdir -p "$DATA_DIR" "$OUT_DIR" "$DRIVE_ROOT/outputs"

if [[ ! -d "$PROJECT_DIR/.git" ]]; then
  git clone "$PROJECT_REPO" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
git pull --ff-only || true
pip install -q -r requirements.txt

if [[ ! -d "$GS_DIR/.git" ]]; then
  git clone https://github.com/graphdeco-inria/gaussian-splatting --recursive "$GS_DIR"
fi

cd "$GS_DIR"
git submodule update --init --recursive
pip install -q plyfile tqdm opencv-python joblib
pip install -q submodules/diff-gaussian-rasterization
pip install -q submodules/simple-knn

if [[ ! -d "$BICYCLE_DATA" ]]; then
  mkdir -p "$DATA_DIR/360_v2"
  wget -c --progress=bar:force:noscroll \
    http://storage.googleapis.com/gresearch/refraw360/360_v2.zip \
    -O "$DATA_DIR/360_v2.zip"
  unzip -q "$DATA_DIR/360_v2.zip" -d "$DATA_DIR/360_v2"
fi

if [[ ! -d "$ASSET_DATA" ]]; then
  if [[ -f "$NERF_ZIP" ]]; then
    unzip -q "$NERF_ZIP" -d "$DATA_DIR"
  else
    echo "NeRF-Synthetic zip not found in Drive; trying public gdown download."
    pip install -q gdown
    if gdown --id "$NERF_SYNTHETIC_GDRIVE_ID" -O "$NERF_DOWNLOAD_ZIP"; then
      unzip -q "$NERF_DOWNLOAD_ZIP" -d "$DATA_DIR"
    else
      echo "Automatic NeRF-Synthetic download failed."
      echo "Google Drive may have blocked public/scripted access."
      echo "Manual fallback:"
      echo "  1. Download NeRF-Synthetic from https://www.matthewtancik.com/nerf"
      echo "  2. Rename it to nerf_synthetic.zip"
      echo "  3. Upload it to Google Drive at MyDrive/HSL_3DGS/nerf_synthetic.zip"
      echo "  4. Mount Drive in Colab before running this script"
      echo "     from google.colab import drive"
      echo "     drive.mount('/content/drive')"
      echo "  5. The script will then see it at $NERF_ZIP"
      echo "  6. Rerun this script"
      exit 1
    fi
  fi
fi

if [[ ! -d "$BICYCLE_DATA" ]]; then
  echo "Bicycle dataset not found after extraction: $BICYCLE_DATA"
  find "$DATA_DIR" -maxdepth 3 -type d | sort | head -50
  exit 1
fi

if [[ ! -d "$ASSET_DATA" ]]; then
  echo "Asset dataset not found after extraction: $ASSET_DATA"
  find "$DATA_DIR" -maxdepth 3 -type d | sort | head -80
  exit 1
fi

cd "$GS_DIR"

if [[ ! -f "$BICYCLE_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply" ]]; then
  python train.py \
    -s "$BICYCLE_DATA" \
    -m "$BICYCLE_MODEL" \
    --eval \
    -i "$BICYCLE_IMAGES" \
    --data_device cpu \
    --iterations "$ITERATIONS" \
    --save_iterations "$ITERATIONS" \
    $TRAIN_EXTRA_ARGS
fi

if [[ ! -f "$ASSET_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply" ]]; then
  python train.py \
    -s "$ASSET_DATA" \
    -m "$ASSET_MODEL" \
    --eval \
    -w \
    --iterations "$ITERATIONS" \
    --save_iterations "$ITERATIONS" \
    $TRAIN_EXTRA_ARGS
fi

cd "$PROJECT_DIR"

SCENE_PLY="$BICYCLE_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply"
ASSET_PLY="$ASSET_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply"
COMPOSED_PLY="$COMPOSED_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply"
TMP_CONFIG="/tmp/hsl_bicycle_${ASSET_NAME}_${MODE}.json"

python - <<PY
import json
config = json.load(open("$PROJECT_DIR/configs/bicycle_chair.json"))
config["scene_ply"] = "$SCENE_PLY"
config["asset_ply"] = "$ASSET_PLY"
config["output_ply"] = "$COMPOSED_PLY"
json.dump(config, open("$TMP_CONFIG", "w"), indent=2)
print(open("$TMP_CONFIG").read())
PY

python tools/scene_stats.py "$SCENE_PLY" --pretty
python tools/scene_stats.py "$ASSET_PLY" --pretty
python tools/compose_splats.py --config "$TMP_CONFIG"

PREVIEW="$OUT_DIR/composed_bicycle_${ASSET_NAME}_${MODE}_bounds.png"
python tools/preview_placement.py \
  --config "$TMP_CONFIG" \
  --out "$PREVIEW"

# Render by copying the Bicycle model directory and replacing only the PLY.
RENDER_MODEL="$OUT_DIR/render_composed_bicycle_${ASSET_NAME}_${MODE}"
rm -rf "$RENDER_MODEL"
cp -r "$BICYCLE_MODEL" "$RENDER_MODEL"
mkdir -p "$RENDER_MODEL/point_cloud/iteration_${ITERATIONS}"
cp "$COMPOSED_PLY" "$RENDER_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply"

cd "$GS_DIR"
python render.py -m "$RENDER_MODEL"

cp -r "$BICYCLE_MODEL" "$DRIVE_ROOT/outputs/"
cp -r "$ASSET_MODEL" "$DRIVE_ROOT/outputs/"
cp -r "$COMPOSED_MODEL" "$DRIVE_ROOT/outputs/"
cp -r "$RENDER_MODEL" "$DRIVE_ROOT/outputs/"
cp "$PREVIEW" "$DRIVE_ROOT/outputs/"

echo "Done."
echo "Saved outputs to: $DRIVE_ROOT/outputs"
echo "Composed PLY: $COMPOSED_PLY"
echo "Rendered model: $RENDER_MODEL"
echo "Log file: $LOG_FILE"
