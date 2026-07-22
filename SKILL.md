---
name: sprite-pet-skill
description: "Create, repair, package, and immediately launch polished animated desktop pets and reusable sprite sets from ideas, reference images, video concepts, or existing art. Covers five anatomy-aware pose rigs, reference-guided 4x2 image sheets, identity locking, chroma cleanup, detached-fragment rejection, within- and cross-action scale calibration, exports, transparent Electron runtimes, and optional pointer/long-press interactions. Use for 制作/修复桌宠, desktop pets, cursor chasing, head/gaze tracking, sprite animation, inconsistent action sizes, identity drift, broken sprite fragments, packaging for macOS/Windows, or requests where the finished pet must already be running."
---

# Sprite Pet Skill

Build the sprite asset pipeline and desktop runtime as separate testable layers. Preserve the anchor, pose guides, raw sheets, prompts, processed frames, and exports.

## 1. Read the method catalog

Read [references/sprite-generator-methods.md](references/sprite-generator-methods.md) completely before acting. It maps every upstream animation method to the Skill implementation and defines the required processing order.

Read [references/prompting-and-motion.md](references/prompting-and-motion.md) before generating images. Read [references/electron-runtime.md](references/electron-runtime.md) only when building or changing the desktop runtime. Read [references/pointer-interactions.md](references/pointer-interactions.md) only when the pet must react to clicks, holds, drags, touch, gaze targets, or pointer direction.

## 2. Choose the body plan and actions

Classify the character by motion anatomy, not visual theme:

- `biped`: humanoids, upright robots and two-legged monsters;
- `quadruped`: cats, dogs, mounts and four-legged beasts;
- `serpent`: snakes, eels, fish and continuous spines;
- `flyer`: birds, bats, winged creatures and hovering fairies;
- `blob`: slimes, ghosts, oozes and squash/stretch characters.

Use the exact action set, FPS, loop, and airborne registry in `scripts/sprite_methods.py`. Do not force a character into the quadruped rig.

## 3. Lock the identity anchor

Use the available image-generation capability. If the host provides a dedicated image-generation skill or tool, invoke it and follow its instructions.

For a generated character, create one definitive 512×512 side-view anchor on pure `#FF00FF`. For existing art, normalize it with:

```bash
python3 scripts/prepare_character_anchor.py <character-image> \
  --output <project>/assets/anchor/raw-magenta.png \
  --transparent-output <project>/assets/anchor/preview.png
```

Do not regenerate the anchor between actions. Changing the anchor invalidates every cached action sheet.

## 4. Render every required pose map

```bash
python3 scripts/generate_pose_guides.py \
  --body-plan <biped|quadruped|serpent|flyer|blob> \
  --actions <comma-list-or-all> \
  --anchor <project>/assets/anchor/raw-magenta.png \
  --output-dir <project>/assets/pose-guides
```

The anchor measurement controls mannequin height, center, and baseline. Use the matching guide together with the same anchor for each action.

## 5. Generate one sheet per action

Generate actions separately as exact 4×2, eight-frame, row-major sheets. Attach the identity anchor first and the action pose guide second. Repeat the invariant identity block verbatim.

Save raw outputs as `<action>.png` under `assets/animation-source`. Require one complete subject per cell, strict cell boundaries, motion in place, stable identity/scale, no grid lines, and pure magenta gutters.

Treat high-deformation actions such as sleep, death, hurt, coil, squash/stretch, and extreme airborne poses as identity checkpoints. Compare age, face geometry, markings, outfit/accessories, body proportions, and rendering against the anchor even when eyes close or the body curls. Pose correctness never excuses identity drift.

After processing, detect duplicates, detached fragments, and identity drift. If any remain, regenerate the action with a concrete count-based fix note. Allow at most two redraws after the first attempt; preserve anchor and pose guide throughout. Retain rejected raw passes with a reason suffix.

## 6. Process the sheets in the upstream order

```bash
python3 -m pip install -r scripts/requirements.txt

python3 scripts/process_sprite_sheets.py \
  --body-plan <plan> \
  --actions <comma-list-or-all> \
  --input-dir <project>/assets/animation-source \
  --output-dir <project>/assets/animations
```

This performs cast-based magenta keying/despill, border removal, safe component isolation, tiny detached-fragment cleanup, diagonal median scale normalization, grounded/airborne alignment, centroid centering, and grid/strip/manifest composition. Use `--prefix` and `--suffix` for alternate source names. Disable fragment cleanup only for an intentionally disconnected identity feature and record that exception.

## 7. Validate, exclude, and export

```bash
python3 scripts/validate_animations.py \
  --animations-dir <project>/assets/animations \
  --body-plan <plan> \
  --actions <comma-list-or-all> \
  --min-gutter 1
```

Audit cross-action scale before accepting playback:

```bash
python3 scripts/audit_sprite_set.py \
  --animations-dir <project>/assets/animations \
  --actions all \
  --reference-action <walk-or-stable-reference>
```

Use bbox diagonal as the pose-stable extent signal and square-root alpha area as the visual-mass signal. Calibrate runtime display scales for comparable locomotion actions; do not force sleep, collapse, impact, squash/stretch, or true airborne poses to the same bounding box. Inspect the actual action transition; metrics propose a correction, not the final aesthetic judgment. After review, persist explicit values with `audit_sprite_set.py --display-scales idle=.95,run=1.08 --write-manifest`; the bundled Electron renderer reads `displayScale`. Re-run validation with the same `--display-scales` before packaging.

Inspect playback as well as automated results. Reject identity drift, clipping, scale pulsing, planted-foot jitter, broken loop seams, missing anticipation/impact/recovery, duplicate subjects, detached alpha fragments, fewer than six meaningful poses, or unexplained scale drift above 8% within the body plan's locomotion scale group. Regenerate missing anatomy or large secondary components; never hide them with cleanup.

Exclude weak frames only when the remaining timing still reads. Exclusions must affect playback and every export:

```bash
python3 scripts/export_sprite_bundle.py \
  --animations-dir <project>/assets/animations \
  --action <action> \
  --exclude <1-based-frame-numbers> \
  --prompt-file <saved-prompt.txt> \
  --output-dir <project>/exports/<action>
```

Deliver per-frame PNGs, transparent grid and strip sheets, ZIP, manifest, prompt set, raw sources, and platform caveats.

## 8. Build the Electron pet when requested

```bash
python3 scripts/scaffold_electron_pet.py --output-dir <project>
```

Copy processed animations into `assets/animations`. Map runtime states to semantic actions supported by the selected body plan. Keep one-shots alive for `frameCount / fps`; tie locomotion cadence to actual movement speed; preserve airborne arcs.

Require click-through transparency, a reachable context menu, pause/return/quit actions, emergency quit shortcut, active-display clamping, strict CSP, and multi-monitor testing.

For pointer-directed head/gaze behavior on raster art, use complete directional character frames by default. Do not cut and rotate a generated head layer: it exposes neck gaps and does not produce real directional facing. Use a separate head bone only when the source is a genuine rig with overlap, masks, pivots, and tested deformation. Freeze window motion immediately on pointer-down, enter the special interaction only after the hold threshold, and restore every state on release, cancel, lost capture, or blur.

## 9. Verify and package

1. Run Python compilation, Node syntax checks, the animation validator, and Skill validation.
2. Test direction flipping, action-boundary scale continuity, one-shot completion, transparent hit testing, menus and display edges.
3. If interactions exist, test every cardinal direction plus diagonals, hold/release/cancel recovery, and prove that the window does not chase or pounce during the hold.
4. Package every requested platform/architecture into a new versioned output; inspect archives and packaged frame contents without overwriting the last accepted build.
5. Distinguish runtime-tested builds from structurally validated cross-platform builds.

## 10. Launch before handoff

Treat launch as part of creation, not as a user follow-up. After the latest current-OS build passes verification, run:

```bash
python3 scripts/launch_desktop_pet.py --project-dir <project>
```

The launcher prefers the newest packaged artifact for the current OS, falls back to `npm start`, recognizes an already-running packaged build, and leaves the process detached. Pass `--artifact <path>` when several builds exist and the newest choice is ambiguous.

Do not mark the task complete until all of these conditions hold:

- the latest current-OS artifact is running and visible;
- the launched process remains alive after the verification wait;
- a screenshot or equivalent visible-state check proves that the transparent window rendered;
- no obsolete test instance is being mistaken for the new build;
- the final response says the pet is already running rather than asking the user to open it.

Do not quit the verified final instance. If the exact artifact is already running, reuse it instead of opening a duplicate. When only cross-platform artifacts can be built, structurally validate those packages but still launch the current-OS artifact. If launching is impossible, report the launch failure as an incomplete result and diagnose it; do not silently downgrade to delivery instructions.

## Provenance

The Sprite animation pipeline is adapted from the MIT-licensed [promptwhisper/sprite-generator](https://github.com/promptwhisper/sprite-generator), pinned at `12a5c31`. Retain [references/provenance.md](references/provenance.md) and the upstream license when redistributing adapted code.
