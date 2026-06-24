#!/usr/bin/env bash
set -euo pipefail

# One-shot Colab runner for the HSL 3DGS composition assignment.
#
# Usage in Colab:
#   !git clone https://github.com/ayushdebnath012/CMU-HSL.git /content/CMU-HSL
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh smoke
#   !bash /content/CMU-HSL/scripts/colab_run_all.sh full
#
# Before running, put nerf_synthetic.zip in:
#   /content/drive/MyDrive/HSL_3DGS/nerf_synthetic.zip

MODE="${1:-smoke}"                 # smoke or full
ASSET_NAME="${ASSET_NAME:-chair}"
PROJECT_REPO="${PROJECT_REPO:-https://github.com/ayushdebnath012/CMU-HSL.git}"
PROJECT_DIR="${PROJECT_DIR:-/content/CMU-HSL}"
GS_DIR="${GS_DIR:-/content/gaussian-splatting}"
DATA_DIR="${DATA_DIR:-/content/data}"
OUT_DIR="${OUT_DIR:-/content/outputs}"
DRIVE_ROOT="${DRIVE_ROOT:-/content/drive/MyDrive/HSL_3DGS}"
NERF_ZIP="${NERF_ZIP:-$DRIVE_ROOT/nerf_synthetic.zip}"

if [[ "$MODE" == "full" ]]; then
  ITERATIONS=30000
  BICYCLE_MODEL="$OUT_DIR/bicycle"
  ASSET_MODEL="$OUT_DIR/$ASSET_NAME"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}"
else
  ITERATIONS=7000
  BICYCLE_MODEL="$OUT_DIR/bicycle_7k"
  ASSET_MODEL="$OUT_DIR/${ASSET_NAME}_7k"
  COMPOSED_MODEL="$OUT_DIR/composed_bicycle_${ASSET_NAME}_7k"
fi

BICYCLE_DATA="$DATA_DIR/360_v2/bicycle"
ASSET_DATA="$DATA_DIR/nerf_synthetic/$ASSET_NAME"

echo "Mode: $MODE"
echo "Iterations: $ITERATIONS"
echo "Asset: $ASSET_NAME"

python - <<'PY'
try:
    from google.colab import drive
    drive.mount("/content/drive")
except Exception as exc:
    print(f"Drive mount skipped or unavailable: {exc}")
PY

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
  wget -c http://storage.googleapis.com/gresearch/refraw360/360_v2.zip -O "$DATA_DIR/360_v2.zip"
  unzip -q "$DATA_DIR/360_v2.zip" -d "$DATA_DIR/360_v2"
fi

if [[ ! -d "$ASSET_DATA" ]]; then
  if [[ ! -f "$NERF_ZIP" ]]; then
    echo "Missing NeRF-Synthetic zip: $NERF_ZIP"
    echo "Upload nerf_synthetic.zip to $DRIVE_ROOT/nerf_synthetic.zip and rerun."
    exit 1
  fi
  unzip -q "$NERF_ZIP" -d "$DATA_DIR"
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
    -i images_4 \
    --data_device cpu \
    --iterations "$ITERATIONS" \
    --save_iterations "$ITERATIONS"
fi

if [[ ! -f "$ASSET_MODEL/point_cloud/iteration_${ITERATIONS}/point_cloud.ply" ]]; then
  python train.py \
    -s "$ASSET_DATA" \
    -m "$ASSET_MODEL" \
    --eval \
    -w \
    --iterations "$ITERATIONS" \
    --save_iterations "$ITERATIONS"
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
python tools/preview_bounds.py \
  --scene "$SCENE_PLY" \
  --asset "$COMPOSED_PLY" \
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

