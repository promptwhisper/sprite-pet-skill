# Sprite Generator method catalog

## Contents

1. Scope and source mapping
2. Body-plan registry
3. Two-stage generation
4. Pose-map conditioning
5. Sheet post-processing
6. Duplicate detection and retry
7. Preview, frame exclusion, caching, and export
8. Methods intentionally outside this Skill

## 1. Scope and source mapping

This catalog covers the complete Sprite animation path from `promptwhisper/sprite-generator` commit `12a5c31f7fc7c224155b0cf1fc2fedbe28b2200e`.

| Capability | Upstream source | Skill implementation |
|---|---|---|
| Body plans, actions, FPS, loop, airborne | `bodyPlans.ts`, `sprite.ts` | `scripts/sprite_methods.py` |
| Shared rig geometry | `rigCore.ts` | `scripts/generate_pose_guides.py` |
| Five anatomy rigs | `rigs/*.ts`, `poseRig.ts` | `scripts/sprite_methods.py`, `scripts/generate_pose_guides.py` |
| Generated/uploaded character anchor | `generate/route.ts`, `SpriteStudio.tsx` | prompting reference, `scripts/prepare_character_anchor.py` |
| Identity + pose-map sheet generation | `generate/route.ts` | prompting reference and Skill workflow |
| Keying and frame cleanup | `imageProcessor.ts`, `SpriteStudio.tsx` | `scripts/process_sprite_sheets.py` |
| Duplicate detection and guided redraw | `SpriteStudio.tsx` | validator plus retry instructions |
| Grid, strip, ZIP, manifest, frame exclusion | `sprite.ts`, `SpriteStudio.tsx` | `scripts/export_sprite_bundle.py` |
| Cross-action scale and fragment QA | Skill hardening from real desktop-pet runtime failures | `scripts/audit_sprite_set.py`, `scripts/validate_animations.py` |
| Pointer/hold/gaze interaction | Desktop runtime extension | `references/pointer-interactions.md`, Electron template |

## 2. Body-plan registry

| Plan | Actions | True airborne actions |
|---|---|---|
| `biped` | idle, walk, run, jump, attack, hurt, death | jump |
| `quadruped` | idle, walk, run, jump, pounce, hurt, death, sleep | jump, pounce |
| `serpent` | idle, slither, strike, coil, hurt, death | none |
| `flyer` | idle, flap, glide, dive, hurt, death | every action |
| `blob` | idle, hop, bounce, lunge, hurt, death | hop, bounce |

Treat `run` as a grounded gait for bipeds and quadrupeds. Preserve ballistic lift only for the actions in the final column. Keep flyers airborne in every action.

## 3. Two-stage generation

Use one locked anchor across every action:

1. Generate a 512×512 pure-magenta anchor, or normalize a user upload.
2. Measure the anchor's non-key height, horizontal center, and baseline.
3. Render the selected action's 4×2 pose-map sheet using the matching anatomy rig and measured subject bounds.
4. Generate a complete sheet with both anchor and pose map attached.
5. Cache results by `bodyPlan:action`; changing a generated anchor invalidates every sheet, while switching actions preserves compatible cached sheets.

For uploaded art, prefer a real transparent PNG. If transparency is absent, remove only background-like pixels connected to image edges: light desaturated checkerboard or a consistent sampled corner color. Then scale inside 84% width × 90% height, center horizontally, seat at 95% of the anchor, and composite over `#FF00FF`.

For image API models, use image edits when references are present and fall back to image generation if edits are unsupported. For multimodal chat models, send identity image, pose map, then text; request image output with low sheet temperature. With a host-provided image-generation tool, attach the same two references and apply the equivalent prompt.

## 4. Pose-map conditioning

Do not ask the image model to invent temporal motion. Render code-authored grey mannequins and ask the model only to skin them.

- Shared conventions: +x right, +y down, character faces right; near limbs light, far limbs dark; dark outline prevents merged parts.
- `biped`: torso/head, two-segment arms and legs; hand-tuned gait curves and one-shot key poses.
- `quadruped`: horizontal spine, neck/head/tail, four phased legs; long-body scale capped by cell width.
- `serpent`: tapered polyline spine driven by traveling sine waves; reach, head tilt, jaw opening.
- `flyer`: pitched body, filled wing surfaces with articulated leading edges, head and tail.
- `blob`: volume-aware squash/stretch, lean, reach, eye direction; no skeleton.
- Safety fit: render every frame on an oversized scratch cell, measure the action-wide union, then apply one shared fit transform to every frame. This preserves relative motion while preventing extreme strike/flap/bounce poses from clipping or crossing cells.

Generate guides with:

```bash
python3 scripts/generate_pose_guides.py \
  --body-plan <plan> \
  --actions all \
  --anchor <raw-magenta-anchor.png> \
  --output-dir <project>/assets/pose-guides
```

## 5. Sheet post-processing

Apply this order exactly:

1. Resize the AI output to the expected 2048×1024 sheet.
2. Slice row-major into eight 512×512 cells.
3. Key magenta with `cast=max(0,min(R,B)-G)`, soft alpha falloff, full R/B despill, and partial green luminance recovery. Use Euclidean distance only for non-magenta custom keys.
4. Remove near-full-span lines inside a thin edge band to erase accidental cell borders.
5. For non-bipeds, keep the dominant central connected alpha component. Enable erosion/split/dilation recovery only for compact quadruped/blob bodies; do not erode serpents or flyers. Remove only tiny detached spillover components (default: at most 2% of the primary and 512 pixels); leave large secondary anatomy visible so validation forces a redraw instead of silently deleting it.
6. Measure each silhouette with row/column noise rejection; use bbox diagonal as pose-stable size; normalize toward median with a 5% dead band and ±18% clamp.
7. Detect the bottom using a multi-row opaque run. Ground each frame individually for grounded actions. For airborne actions, align the 85th-percentile grounded reference once and apply the same rigid vertical shift to every frame.
8. Center by opaque-pixel horizontal centroid rather than bbox midpoint, preserving thin weapons, tails, and extended limbs.
9. Audit comparable actions across the full set. Within-action normalization cannot prevent idle/walk/run from depicting the same character at different apparent sizes.

Run with:

```bash
python3 scripts/process_sprite_sheets.py \
  --body-plan <plan> \
  --actions <comma-list-or-all> \
  --input-dir <project>/assets/animation-source \
  --output-dir <project>/assets/animations
```

## 6. Duplicate detection and retry

Downsample alpha to 100×100, build row/column mass profiles, and detect two substantial segments separated by at least 5% of the cell dimension. Treat a second segment with at least 45% of the primary mass as duplicate/spillover risk.

After the first sheet:

1. Process and inspect all cells.
2. If duplicate/spillover cells remain, regenerate the entire action with a fix note giving the count and restating one complete subject per cell, strict boundaries, smaller scale, and magenta gutters.
3. Repeat at most twice more. Preserve the same identity anchor and pose guide.

Do not silently accept a bad third pass; report the failed action and keep the raw sheet for diagnosis.

Also count alpha-connected components after final alignment. A small isolated tail/head/limb fragment can evade mass-profile duplicate detection. Remove tiny sheet spillover deterministically, but regenerate if the secondary component could be real anatomy or identity detail.

Run `scripts/audit_sprite_set.py` after processing. Compare bbox diagonal and square-root alpha area, then visually inspect action transitions. Apply reviewed runtime `displayScale` values only to comparable locomotion actions; do not normalize away intentional collapse, curl, squash/stretch, or airborne reach.

## 7. Preview, frame exclusion, caching, and export

- Preview only frames with images and `disabled != true`.
- Allow per-animation FPS from 1–30; initialize with registry defaults.
- A disabled frame is absent from playback and every export, not merely hidden in the UI.
- Export transparent row-major grid, one-row strip, numbered PNGs, and manifest.
- Manifest records body plan, animation, FPS, frame duration, loop, source indices, grid/strip coordinates, prompt, and excluded source frames.
- ZIP contains `frame_01.png...`, `sheet.png`, `strip.png`, and `manifest.json`.

Use:

```bash
python3 scripts/export_sprite_bundle.py \
  --animations-dir <project>/assets/animations \
  --action <action> \
  --exclude 3,6 \
  --output-dir <project>/exports/<action>
```

## 8. Methods intentionally outside this Skill

The upstream repository also contains canvas outpainting, Poisson seam blending, parallax extension, and tileable-texture utilities. Those are image/background-production methods, not Sprite animation generation, so they are not invoked by this desktop-pet Skill.
