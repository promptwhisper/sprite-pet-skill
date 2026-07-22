# Sprite generation prompts and motion rules

Read `scripts/sprite_methods.py` for the authoritative plan/action/FPS registry and [sprite-generator-methods.md](sprite-generator-methods.md) for the full pipeline.

## Anchor prompt

```text
Create one definitive CHARACTER REFERENCE IMAGE for a 2D side-view sprite animation pipeline.

POSE:
- [Insert BODY_PLANS[body_plan].anchor].
- Show the complete silhouette with generous pure-magenta margins.

STYLE:
- Preserve the user's requested style. Prefer crisp game-readable shapes and clean edges.
- Side-view only. No text, UI, labels, watermark, ground plane, or cast shadow.

BACKGROUND:
- Every pixel outside the silhouette is perfectly flat #FF00FF (255,0,255).
- Never use pure magenta inside the character.

CHARACTER:
[Identity description]

Output exactly one complete character at 512×512.
```

Do not force pixel art when the user requested illustration, anime, painterly, sticker, or another style. Keep the upstream structural rules while preserving the chosen visual language.

## Sheet prompt

```text
Create one complete 2D side-view animation sprite sheet.

CANVAS:
- Exactly 4 columns × 2 rows, 8 chronological frames, row-major.
- Each cell represents 512×512 after normalization.

REFERENCES:
- IMAGE 1 is the immutable identity anchor. Preserve outfit, color, proportions, face, markings,
  accessories, rendering style, outline and lighting in every frame.
- IMAGE 2 is the pose map. Follow each grey mannequin's structure exactly.
- [Insert BODY_PLANS[body_plan].guidance].
- The pose map controls structure; the identity image controls appearance. Do not draw the mannequin.

ANIMATION:
- [Action, loop/one-shot, default FPS].
- [Insert ACTIONS[action].choreography].

STRICT RULES:
- Exactly one complete character per cell. No twins, echoes, reflections or cropped spillover.
- Each character is one anatomically continuous subject. No detached head, limb, tail, clothing piece, or neighbouring-cell fragment unless the identity intentionally contains a disconnected feature.
- Nothing crosses a cell boundary. Locomotion happens in place.
- Same identity, scale and horizontal center in every cell.
- Keep a pure-magenta gutter around every silhouette; shrink long creatures instead of cropping.
- No visible grid or cell borders. No text or labels.
- Flat #FF00FF everywhere outside the character; no shadow, glow, texture or gradient.

CHARACTER:
[Repeat the invariant identity description verbatim]

[Optional retry fix notes]
```

## Model routing

- Built-in image generator: attach anchor and pose guide as references and generate each action separately.
- Image edit endpoint: use when both references can be supplied as image inputs.
- Image generation endpoint: use for the anchor or as a fallback when edit is unsupported.
- Multimodal chat image output: send anchor, pose map, then prompt; keep sheet creativity low.

Always preserve raw outputs, exact prompts, model name, body plan, action, and retry notes for reproducibility.

## Identity checkpoints

Audit identity most aggressively when pose hides the usual evidence: sleep/closed eyes, death/collapse, hurt/recoil, coils, squash/stretch, foreshortening, and extreme airborne poses.

Compare against the immutable anchor, not against the previous generated action. Check:

- apparent age and species/breed;
- head-to-body ratio, muzzle/jaw shape, eye spacing, ears/horns;
- invariant markings, palette, outfit, accessories, and tail tip;
- rendering language, edge treatment, outline, and lighting.

If an action reads as a different character, redraw the whole action with a targeted note naming the drift. Preserve the original anchor and pose guide. Closed eyes, curled posture, or impact deformation never justify a different face or body type.
