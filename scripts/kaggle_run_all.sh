#!/usr/bin/env bash
set -euo pipefail

# Kaggle runner for the HSL 3DGS composition assignment.
#
# Kaggle setup:
#   1. Notebook Settings -> Accelerator -> GPU.
#   2. Notebook Settings -> Internet -> On.
#   3. Add a Kaggle Dataset input containing nerf_synthetic.zip, or an
#      extracted nerf_synthetic/chair folder.
#
# Usage in a Kaggle notebook cell:
#   !git clone https://github.com/ayushdebnath012/CMU-HSL.git /kaggle/working/CMU-HSL || true
#   !bash /kaggle/working/CMU-HSL/scripts/kaggle_run_all.sh t4full

if [[ "${DEBUG:-0}" == "1" ]]; then
  set -x
fi

LOG_FILE="${LOG_FILE:-/kaggle/working/hsl_kaggle_run.log}"
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1
trap 'status=$?; echo; echo "ERROR: kaggle_run_all.sh failed at line $LINENO with exit code $status"; echo "Inspect log with: tail -n 160 $LOG_FILE"; exit $status' ERR

MODE="${1:-t4full}"                # lite, smoke, t4full, or full
ASSET_NAME="${ASSET_NAME:-chair}"
ASSET_SCALE="${ASSET_SCALE:-0.06}"
ASSET_RX="${ASSET_RX:-0.0}"
ASSET_RY="${ASSET_RY:-0.0}"
ASSET_RZ="${ASSET_RZ:-0.0}"
ASSET_TX="${ASSET_TX:-0.0}"
ASSET_TY="${ASSET_TY:-0.0}"
ASSET_TZ="${ASSET_TZ:-0.0}"
ASSET_OPACITY="${ASSET_OPACITY:-0.55}"
RUN_TAG="${RUN_TAG:-}"

PROJECT_REPO="${PROJECT_REPO:-https://github.com/ayushdebnath012/CMU-HSL.git}"
PROJECT_DIR="${PROJECT_DIR:-/kaggle/working/CMU-HSL}"
GS_DIR="${GS_DIR:-/kaggle/working/gaussian-splatting}"
DATA_DIR="${DATA_DIR:-/kaggle/working/data}"
OUT_DIR="${OUT_DIR:-/kaggle/working/outputs}"
EXPORT_DIR="${EXPORT_DIR:-/kaggle/working/hsl_outputs}"
NERF_DOWNLOAD_ZIP="${NERF_DOWNLOAD_ZIP:-$DATA_DIR/nerf_synthetic.zip}"
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

if [[ -n "$RUN_TAG" ]]; then
  COMPOSED_MODEL="${COMPOSED_MODEL}_${RUN_TAG}"
fi

BICYCLE_DATA="$DATA_DIR/360_v2/bicycle"
ASSET_DATA="$DATA_DIR/nerf_synthetic/$ASSET_NAME"

echo "Mode: $MODE"
echo "Iterations: $ITERATIONS"
echo "Asset: $ASSET_NAME"
echo "Bicycle image folder: $BICYCLE_IMAGES"
echo "Extra train args: $TRAIN_EXTRA_ARGS"
echo "Log file: $LOG_FILE"
echo "Asset transform: scale=$ASSET_SCALE rotation=[$ASSET_RX,$ASSET_RY,$ASSET_RZ] translation=[$ASSET_TX,$ASSET_TY,$ASSET_TZ] opacity=$ASSET_OPACITY"

python - <<'PY'
import torch
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    raise SystemExit("No CUDA GPU available. In Kaggle, enable GPU in Notebook Settings.")
PY

mkdir -p "$DATA_DIR" "$OUT_DIR" "$EXPORT_DIR"

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
  BICYCLE_ZIP="$DATA_DIR/360_v2.zip"
  wget -c --progress=bar:force:noscroll \
    http://storage.googleapis.com/gresearch/refraw360/360_v2.zip \
    -O "$BICYCLE_ZIP"
  python - <<PY
from pathlib import Path
from zipfile import ZipFile

zip_path = Path("$BICYCLE_ZIP")
out_dir = Path("$DATA_DIR/360_v2")
with ZipFile(zip_path) as zf:
    names = zf.namelist()
    bike_names = [
        n for n in names
        if n.startswith("bicycle/") or n.startswith("360_v2/bicycle/")
    ]
    if not bike_names:
        raise SystemExit("Could not find bicycle/ folder in 360_v2.zip")
    for name in bike_names:
        target_name = name
        if target_name.startswith("360_v2/"):
            target_name = target_name[len("360_v2/"):]
        if target_name.endswith("/"):
            continue
        target = out_dir / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(name) as src, target.open("wb") as dst:
            dst.write(src.read())
print(f"Extracted {len(bike_names)} Bicycle entries to {out_dir}")
PY
  rm -f "$BICYCLE_ZIP"
fi

if [[ ! -d "$ASSET_DATA" ]]; then
  FOUND_ASSET="$(find /kaggle/input "$DATA_DIR" -path "*/nerf_synthetic/$ASSET_NAME/transforms_train.json" -print -quit 2>/dev/null || true)"
  if [[ -n "$FOUND_ASSET" ]]; then
    FOUND_ASSET_DIR="$(dirname "$FOUND_ASSET")"
    if [[ "$FOUND_ASSET_DIR" == /kaggle/input/* ]]; then
      ASSET_DATA="$DATA_DIR/nerf_synthetic/$ASSET_NAME"
      echo "Copying read-only Kaggle input asset to writable path: $ASSET_DATA"
      mkdir -p "$(dirname "$ASSET_DATA")"
      rm -rf "$ASSET_DATA"
      cp -r "$FOUND_ASSET_DIR" "$ASSET_DATA"
    else
      ASSET_DATA="$FOUND_ASSET_DIR"
      echo "Using extracted NeRF-Synthetic asset: $ASSET_DATA"
    fi
  else
    NERF_ZIP="$(find /kaggle/input "$DATA_DIR" -iname "nerf_synthetic.zip" -print -quit 2>/dev/null || true)"
    if [[ -n "$NERF_ZIP" ]]; then
      echo "Extracting NeRF-Synthetic zip: $NERF_ZIP"
      unzip -q "$NERF_ZIP" -d "$DATA_DIR"
    else
      echo "NeRF-Synthetic zip not found in Kaggle inputs; trying public gdown download."
      pip install -q gdown
      if gdown --id "$NERF_SYNTHETIC_GDRIVE_ID" -O "$NERF_DOWNLOAD_ZIP"; then
        unzip -q "$NERF_DOWNLOAD_ZIP" -d "$DATA_DIR"
      else
        echo "Automatic NeRF-Synthetic download failed."
        echo "Upload nerf_synthetic.zip as a Kaggle Dataset, then Add Input to this notebook."
        echo "Expected asset folder after extraction: nerf_synthetic/$ASSET_NAME"
        exit 1
      fi
    fi
  fi
fi

if [[ ! -d "$BICYCLE_DATA" ]]; then
  echo "Bicycle dataset not found: $BICYCLE_DATA"
  find "$DATA_DIR" -maxdepth 4 -type d | sort | head -80
  exit 1
fi

if [[ ! -d "$ASSET_DATA" ]]; then
  echo "Asset dataset not found: $ASSET_DATA"
  find /kaggle/input "$DATA_DIR" -maxdepth 5 -type d | sort | head -120
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
config["asset_transform"]["scale"] = float("$ASSET_SCALE")
config["asset_transform"]["rotation_degrees"] = [
    float("$ASSET_RX"),
    float("$ASSET_RY"),
    float("$ASSET_RZ"),
]
config["asset_transform"]["translation"] = [
    float("$ASSET_TX"),
    float("$ASSET_TY"),
    float("$ASSET_TZ"),
]
config["appearance"]["opacity_multiplier"] = float("$ASSET_OPACITY")
json.dump(config, open("$TMP_CONFIG", "w"), indent=2)
print(open("$TMP_CONFIG").read())
PY

python tools/scene_stats.py "$SCENE_PLY" --pretty
python tools/scene_stats.py "$ASSET_PLY" --pretty
python tools/compose_splats.py --config "$TMP_CONFIG"

PREVIEW_SUFFIX="${MODE}"
if [[ -n "$RUN_TAG" ]]; then
  PREVIEW_SUFFIX="${PREVIEW_SUFFIX}_${RUN_TAG}"
fi
PREVIEW="$OUT_DIR/composed_bicycle_${ASSET_NAME}_${PREVIEW_SUFFIX}_bounds.png"
python tools/preview_placement.py \
  --config "$TMP_CONFIG" \
  --out "$PREVIEW"

RENDER_MODEL="$OUT_DIR/render_composed_bicycle_${ASSET_NAME}_${MODE}"
if [[ -n "$RUN_TAG" ]]; then
  RENDER_MODEL="${RENDER_MODEL}_${RUN_TAG}"
fi
rm -rf "$RENDER_MODEL"
cp -r "$BICYCLE_MODEL" "$RENDER_MODEL"
mkdir -p "$RENDER_MODEL/point_cloud/iteration_${ITERATIONS}"
cp "$COMPOSED_PLY" "$RENDER_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply"

cd "$GS_DIR"
python render.py -m "$RENDER_MODEL"

cp -r "$BICYCLE_MODEL" "$EXPORT_DIR/"
cp -r "$ASSET_MODEL" "$EXPORT_DIR/"
cp -r "$COMPOSED_MODEL" "$EXPORT_DIR/"
cp -r "$RENDER_MODEL" "$EXPORT_DIR/"
cp "$PREVIEW" "$EXPORT_DIR/"

echo "Done."
echo "Saved outputs to: $EXPORT_DIR"
echo "Composed PLY: $COMPOSED_PLY"
echo "Rendered model: $RENDER_MODEL"
echo "Log file: $LOG_FILE"
