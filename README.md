# Sprite Pet Skill

English | [简体中文](README.zh-CN.md)

Turn any character image into a polished, animated, interactive desktop pet.

This repository goes beyond prompting. It provides an end-to-end workflow for motion design, sprite processing, quality validation, an Electron desktop runtime, packaging, and launch verification.

## What it solves

The hard part of generating a desktop pet is not merely making a character move. Every action must still look like the same character, remain visually consistent, and behave predictably on the desktop. Sprite Pet Skill addresses common failures such as:

- Idle, walk, and run animations changing apparent character size;
- identity drift in sleep, hurt, death, or curled poses;
- detached tail fragments, grid lines, or clipped silhouettes in transparent frames;
- repeated pouncing and jitter when the pointer stops moving;
- broken necks caused by cutting and rotating a head from a flat image;
- delivering sprite assets without packaging and launching the actual pet.

## Features

- Five motion-aware body plans: `biped`, `quadruped`, `serpent`, `flyer`, and `blob`;
- identity anchors and pose guides for separate 4×2, eight-frame action sheets;
- magenta keying, despill, grounding, centering, and transparent frame export;
- checks for identity drift, duplicate frames, detached fragments, unsafe gutters, and weak loops;
- cross-action scale auditing for idle, walk, and run with persistent `displayScale` calibration;
- complete eight-direction long-press gaze art that avoids fake head rotation;
- an Electron template with click-through transparency, menus, display clamping, and stable pointer-following behavior;
- structured macOS and Windows packaging with current-OS launch verification.

## Installation

Clone the repository into a skills directory where your AI agent can discover `SKILL.md`:

```bash
git clone https://github.com/promptwhisper/sprite-pet-skill.git \
  <skills-directory>/sprite-pet-skill
```

Install the image-processing dependency:

```bash
python3 -m pip install -r \
  <skills-directory>/sprite-pet-skill/scripts/requirements.txt
```

Skill directories and invocation syntax vary by host. If your host supports explicit skill calls, invoke `$sprite-pet-skill`; otherwise describe the desktop-pet task in natural language.

The core workflow uses only `SKILL.md`, `scripts/`, `references/`, and `assets/`, so it is not tied to a specific agent. `agents/openai.yaml` is optional host UI metadata and does not affect use in other environments.

## Example prompts

```text
Use $sprite-pet-skill to turn this cat image into a desktop pet with idle, walk, run, and pointer-chasing animations. Package and launch it when finished.
```

```text
Repair this desktop pet: idle is larger than walk, run is smaller than walk, and the pet repeatedly pounces when the pointer stays still.
```

```text
While I long-press the pet, freeze it in place and make its head naturally face the pointer in eight directions. Do not cut out and rotate the head.
```

```text
Use $sprite-pet-skill to turn this dragon image into a scale-consistent desktop pet with idle, walk, run, chase, and eight-direction long-press gaze interactions. Package and launch it.
```

## Workflow

```text
Character image or concept
          ↓
Identity anchor + body-plan selection
          ↓
Pose guides + separate eight-frame action sheets
          ↓
Transparency, alignment, scale normalization, fragment handling
          ↓
Cross-action audit + visual playback review
          ↓
Electron desktop-pet runtime
          ↓
Package, validate, and launch
```

See [SKILL.md](SKILL.md) for the complete operating procedure. See [pointer-interactions.md](references/pointer-interactions.md) for the interaction model and [electron-runtime.md](references/electron-runtime.md) for desktop runtime constraints.

## Included tools

| Tool | Purpose |
| --- | --- |
| `prepare_character_anchor.py` | Normalize a character image into a stable identity anchor |
| `generate_pose_guides.py` | Generate pose guides for each body plan and action |
| `process_sprite_sheets.py` | Process, align, and export animation frames and manifests |
| `validate_animations.py` | Detect duplicates, clipping, fragments, and scale drift |
| `audit_sprite_set.py` | Audit cross-action scale and persist display calibration |
| `export_sprite_bundle.py` | Export frames, grids, strips, ZIP files, and prompts |
| `scaffold_electron_pet.py` | Create a transparent Electron desktop-pet project |
| `launch_desktop_pet.py` | Launch the newest viable build for the current OS |

Inspect any command before running it:

```bash
python3 scripts/<tool-name>.py --help
```

## Design principles

1. Character identity takes priority over pose exaggeration.
2. Equal canvas dimensions do not imply equal visual size; audit the actual silhouette and visual mass.
3. Remove only tiny, unambiguous alpha fragments automatically. Regenerate anything that may be a tail, ear, wing, or limb.
4. Use complete character frames for directional tracking on flat PNG art. Rotate a separate head only when the source is a genuine rig with authored overlap, masks, and pivots.
5. Generation, validation, packaging, and launch are one delivery workflow.

## Requirements

- Python 3 and Pillow;
- an image-generation capability that accepts reference images;
- Node.js and npm when building the Electron desktop runtime;
- Electron template versions are pinned in `assets/electron-template/package.json`.

## Provenance

The sprite-animation methods are adapted from the MIT-licensed [promptwhisper/sprite-generator](https://github.com/promptwhisper/sprite-generator). See [provenance.md](references/provenance.md) for the pinned source commit and adaptation scope, and [UPSTREAM_LICENSE.txt](references/UPSTREAM_LICENSE.txt) for the upstream license.
