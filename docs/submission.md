# Submission Checklist

## Required Deliverables

- GitHub repository: `https://github.com/ayushdebnath012/CMU-HSL`
- 3-slide deck: `presentation/HSL_Technical_Assessment_3DGS_Composition.pptx`
- Final render: `hsl_final_result.png`
- Process notes: `docs/process.md`
- Reproducible runners:
  - `scripts/kaggle_run_all.sh`
  - `scripts/colab_run_all.sh`

## Before Sending

The assignment asks for a private GitHub repository with these collaborators:

- `saswat0`
- `aviralchharia`

If GitHub CLI is logged in, run:

```bash
gh repo edit ayushdebnath012/CMU-HSL --visibility private --accept-visibility-change-consequences
gh api -X PUT repos/ayushdebnath012/CMU-HSL/collaborators/saswat0 -f permission=push
gh api -X PUT repos/ayushdebnath012/CMU-HSL/collaborators/aviralchharia -f permission=push
```

Or do it from GitHub:

1. Repository settings -> General -> Danger Zone -> Change visibility -> Private.
2. Repository settings -> Collaborators -> Add `saswat0` and `aviralchharia`.

## What To Defend In The Call

The core idea is splat-level composition, not image compositing.

```text
p_scene = s R p_asset + t
```

For each foreground Gaussian:

- center is transformed by the similarity transform
- log-scales receive `+ log(s)`
- quaternion rotation is left-multiplied by the placement rotation
- opacity is edited in alpha space and mapped back to raw opacity
- the transformed foreground Gaussians are appended to the scene Gaussians

The merged `point_cloud.ply` is rendered with the original Bicycle cameras, so scene and object Gaussians are depth-sorted and alpha-composited in one rasterizer pass.

## Expected Limitations

- Bicycle/COLMAP and NeRF-Synthetic/Blender do not share a metric scale.
- The inserted object can look like a noisy splat blob because the source asset and real scene have different lighting and reconstruction quality.
- Soft splats and floaters can create imperfect occlusion near vegetation and thin geometry.
- The placement is defensible as a baseline because it is explicit, reproducible, and stored in config/environment variables.

## Novel Extension

Keep the transformed geometry fixed, then optimize a small asset-only appearance correction over spherical harmonic color coefficients. The objective would make the asset match local Bicycle scene brightness and color temperature from rendered feedback, while preserving the object identity.

