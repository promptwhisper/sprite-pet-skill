# Pointer, hold, drag, and gaze interactions

Use this reference only when the pet reacts directly to pointer input.

## Choose the deformation model

Prefer the least fragile model that can express the requested motion:

1. **Complete directional raster frames**: default for generated PNG sprites. Generate one intact subject per direction; swap the whole image.
2. **Real skeletal/mesh rig**: use only when the supplied asset already has bones, overlap, masks, pivots, and deformable geometry.
3. **Layered raster parts**: use only for deliberately authored puppet art with hidden overlap under every joint. Do not derive it by cutting a finished flat sprite.

Never cut a head out of a finished generated frame and rotate it in CSS. Rotation exposes the missing neck, duplicates edge fur, and merely tilts the face instead of turning it toward the target.

## Generate a directional look set

For a general 2D pet, generate a dedicated 4×2 sheet of eight complete poses. Keep body, feet, tail, baseline, scale, identity, and lighting fixed; change only head/chin orientation and eye gaze.

Use this row-major order:

1. up-left
2. up
3. up-right
4. right
5. down-right
6. down
7. down-left
8. left

For a body that normally faces right, require the final left-look frame to keep the same body orientation and turn the head naturally over the shoulder. Do not accept a full-body mirror unless the interaction explicitly allows the body to turn.

Save:

```text
assets/interaction-source/look.png
assets/interaction/look/frame-00.png ... frame-07.png
prompts/look.txt
assets/interaction-source/rejected/<reason>.png
```

Process and validate the sheet with the same keying, component, gutter, scale, and identity rules as semantic actions. A directional sheet is interaction state, not a replacement for idle.

## Map the pointer to frames

Sample the screen cursor in the main process. Normalize from the pet-window center with independent horizontal and vertical ranges, clamp both axes to `[-1, 1]`, and use `atan2(y, x)` to select the nearest octant.

For the frame order above:

```js
function lookFrameIndex(x, y) {
  if (Math.hypot(x, y) < 0.12) return 3;
  const octant = Math.round(Math.atan2(y, x) / (Math.PI / 4));
  return ((octant + 3) % 8 + 8) % 8;
}
```

Preload every directional frame. Do not let ordinary velocity-based `scaleX(-1)` flip this fixed-body set unless the mapping is also transformed and the body turn is intended.

## Long-press state contract

Separate `holding` from the activated interaction:

- On primary pointer-down over the visible pet, set `holding=true` immediately. Freeze velocity, cancel pounce/catch/sleep transitions, and force the window interactive.
- After 350–500 ms, set the requested mode such as `teasing=true`.
- While holding, keep the window fixed and update only the directional sprite or real rig.
- On pointer-up, pointer-cancel, lost pointer capture, window blur, or visibility loss, clear both states and timers.
- Re-arm chase/pounce only after a safe cooldown or after the pointer leaves the configured radius.

Use pointer capture so release is observed after dragging outside the visible silhouette. Keep IPC narrow and verify the sender in the main process.

## Verification

Test all eight directions from a packaged build. During a held interaction verify:

- the window position remains constant;
- the expected frame index is selected for up/right/down/left and diagonals;
- the subject is one continuous silhouette with no detached components;
- release and cancel restore ordinary behavior exactly once;
- a short click does not accidentally enter long-press mode;
- the context menu and emergency quit remain reachable.
