# Three-Slide Presentation Outline

## Slide 1: Problem And Training

- Objective: compose a real Bicycle scene and a separate synthetic foreground object using 3DGS.
- Background: 3DGS represents scenes as anisotropic Gaussians with learned position, scale, rotation, opacity, and spherical harmonic color.
- Training setup:
  - Bicycle: Mip-NeRF 360 scene, COLMAP-style cameras, `--eval -i images_4`.
  - Chair: NeRF-Synthetic object, Blender transforms, `--eval -w`.
- Deliverable status: training scripts are included; full training requires CUDA/conda.

## Slide 2: Composition Method

- Transform foreground Gaussian centers with `p_scene = s R p_object + t`.
- Update Gaussian internals:
  - log-scales receive `+ log(s)`.
  - rotations receive placement quaternion multiplication.
  - opacity and SH color receive optional appearance adjustment.
- Merge scene and asset into one `point_cloud.ply`.
- Render merged model with the original 3DGS rasterizer for consistent depth/alpha ordering.

## Slide 3: Results, Bottlenecks, Extension

- Scale is ambiguous across datasets because each reconstruction has its own similarity gauge.
- Used bounding boxes plus visual anchors, then iterative placement.
- Bottlenecks:
  - CUDA training requirements.
  - soft splat occlusion near intersections.
  - color mismatch between real outdoor scene and synthetic object.
- Novel extension: optimize a small asset-only SH/exposure correction from composed render feedback.

