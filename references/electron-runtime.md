# Electron runtime guide

## Architecture

Keep cursor sampling and window movement in Electron's main process. Send only compact semantic state to the renderer:

```text
main process: cursor/display → steering → pose, direction, speed
renderer: pose → animation → frame cadence → image element
```

Use a transparent, frameless, fixed-size, always-on-top `BrowserWindow`. Enable `contextIsolation`, disable `nodeIntegration`, and expose only narrow IPC methods through the preload script.

Acquire Electron's single-instance lock before creating the window. When a second launch is attempted, keep the existing pet and surface its window instead of creating a duplicate.

## Behavior state machine

Use distance thresholds with cooldowns:

- outside chase radius: idle or wander near the bottom edge;
- inside chase radius: run toward cursor;
- inside pounce radius and cooldown elapsed: play the full pounce one-shot;
- inside catch radius: play success reaction, then return to chase/idle;
- paused: damp velocity and hold idle.

Avoid switching a one-shot action based only on current distance; store an `actionUntil` deadline based on `frameCount / fps`.

Use arrival steering with a slow radius and a nonzero stop radius. Settle at a stable follow ring instead of accelerating through the cursor; gently retreat if a catch leaves the pet inside that ring. After a pounce, keep it disarmed until the pointer moves beyond a larger re-arm radius. A cooldown alone does not prevent repeated jumping around a stationary cursor.

Tie locomotion FPS to actual speed within a bounded range. Flip the character with `scaleX(-1)` based on horizontal velocity; do not generate a duplicate left-facing sheet.

Keep cross-action display scale explicit. Prefer reviewed per-animation `displayScale` values in the manifest; persist them with `audit_sprite_set.py --display-scales ... --write-manifest`. The bundled renderer reads these values. Apply scale and direction in the same composed transform so one does not overwrite the other. Compare idle→walk→run transitions in the packaged window; do not infer continuity from equal 512×512 canvases.

For click, hold, drag, touch, or gaze tracking, read [pointer-interactions.md](pointer-interactions.md). Freeze locomotion on pointer-down before a long-press timer can fire. Generated flat raster sprites should use complete directional frames; reserve part rotation for a real authored rig.

## Desktop safety and usability

- Make transparent window areas click-through.
- Keep a small visible interaction area for the context menu.
- Provide pause, return-home, and exit actions.
- Register an emergency global quit shortcut.
- Clamp the window to the active display work area.
- Re-evaluate the display after movement for multi-monitor setups.
- Use a strict Content Security Policy.
- Reset held/dragged interaction state on release, cancel, lost capture, blur, and renderer teardown.

## Packaging

Pin Electron and packager versions for reproducible output. Package from a clean source folder and exclude `dist`. Use platform-native icons when available. On macOS, explain unsigned-app Gatekeeper behavior. On Windows, distribute the complete packaged folder or its ZIP rather than the `.exe` alone.

Runtime-test on the current OS. On other operating systems, verify executable format, archive integrity, packaged animation assets, and clearly label the lack of an actual launch test.

## Launch and handoff contract

Creation is complete only when the newest current-OS build is visibly running. Use `scripts/launch_desktop_pet.py --project-dir <project>` after packaging; use `--artifact` when auto-discovery could select the wrong build.

The launcher must prefer a packaged build, detach it from the invoking shell, wait long enough to catch immediate crashes, and avoid duplicating an exact running artifact. Do not terminate the final verified process. Capture a screenshot or perform an equivalent visible-window check after process verification. Final delivery may include fallback launch instructions, but it must not delegate the first launch to the user.
