# Process Notes

## Goal

Compose two separately trained 3D Gaussian Splatting assets with plausible spatial consistency:

1. Train a 3DGS background on Mip-NeRF 360 `bicycle`.
2. Train a 3DGS foreground object on a NeRF-Synthetic asset, default `chair`.
3. Insert the object into the Bicycle reconstruction by transforming and merging its Gaussians.
4. Render the merged model from Bicycle cameras so depth and alpha composition happen in one rasterization pass.

## Training Plan

Use the official Graphdeco implementation. The Bicycle dataset is a COLMAP-style real scene. The NeRF-Synthetic object uses `transforms_*.json` camera metadata and should be trained with white background enabled.

Commands:

```powershell
.\scripts\setup_3dgs.ps1
conda activate gaussian_splatting
.\scripts\train_bicycle.ps1
.\scripts\train_asset.ps1 -Dataset data/nerf_synthetic/chair -Output outputs/chair
```

This local checkout could not run those commands fully because `conda` and `nvidia-smi` were unavailable. The scripts are ready for a CUDA workstation.

## Coordinate Transform

The insertion transform is:

```text
p_scene = s R p_asset + t
```

where `s` is uniform scale, `R` is an Euler-derived rotation matrix, and `t` is translation in the Bicycle scene coordinate frame.

The implementation applies the same transform to Gaussian centers and updates the internal anisotropic Gaussian parameters:

- Gaussian log-scales receive `+ log(s)`.
- Gaussian rotations receive `q_place * q_asset`.
- Raw opacity is treated as pre-sigmoid opacity, so opacity edits are done in alpha space and mapped back with `logit`.

## Scale Reasoning

Both datasets have camera calibration, but they do not share a common physical ruler. The Bicycle scene comes from COLMAP/SfM scale, which is arbitrary up to a similarity transform. NeRF-Synthetic assets also live in their own normalized Blender coordinate system.

The baseline scale procedure is:

1. Compute bounding boxes for scene and asset with `tools/scene_stats.py`.
2. Choose a plausible target size in scene units using visual anchors, such as bicycle wheel diameter, ground plane, or camera height.
3. Set the initial object scale from the ratio between desired scene extent and object bounding-box extent.
4. Refine interactively using rendered views from original Bicycle cameras.

This is a defensible choice because the ambiguity is real: calibration constrains each reconstruction internally, but not the cross-dataset similarity transform.

## Occlusion And Rasterization Conflicts

The baseline avoids 2D image compositing. Instead, it writes one merged `point_cloud.ply` and uses the original 3DGS rasterizer. This lets the renderer alpha-composite scene and asset Gaussians in the same pass.

Expected issues:

- Floaters in either reconstruction can appear in front of the inserted object.
- Thin geometry may not occlude cleanly because splats are soft ellipsoids.
- If the asset intersects scene splats, depth order can flicker or look muddy.

Mitigations:

- Place the asset on a surface with some spatial margin.
- Lower asset opacity slightly if it looks too pasted on.
- Adjust `f_dc_*` color multipliers to match scene exposure.
- Optionally prune scene Gaussians inside a small asset bounding volume as a future extension.

## Novel Extension Idea

Learn a small placement-aware appearance correction for the inserted object. Keep geometry fixed, render the composed model from several Bicycle cameras, and optimize only a low-dimensional color/exposure transform for the asset SH coefficients. The objective would match local scene brightness and color temperature around the insertion region while preserving the asset identity.

