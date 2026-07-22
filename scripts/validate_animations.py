#!/usr/bin/env python3
"""Validate animation frames, continuity, fragments, and cross-action scale."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image

from sprite_methods import BODY_PLANS


ALPHA_THRESHOLD = 48
COMPONENT_THRESHOLD = 8


def names(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_display_scales(value):
    result = {}
    if not value:
        return result
    for item in names(value):
        try:
            action, raw_scale = item.split("=", 1)
            scale = float(raw_scale)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("display scales must use action=number") from exc
        if scale <= 0:
            raise argparse.ArgumentTypeError("display scales must be positive")
        result[action.strip()] = scale
    return result


def digest(image):
    return hashlib.sha256(image.tobytes()).hexdigest()


def subject_bbox(image):
    return image.getchannel("A").point(
        lambda value: 255 if value > ALPHA_THRESHOLD else 0
    ).getbbox()


def component_sizes(image, threshold=COMPONENT_THRESHOLD):
    alpha = image.getchannel("A")
    width, height = image.size
    values = alpha.tobytes()
    occupied = bytearray(1 if value > threshold else 0 for value in values)
    seen = bytearray(width * height)
    sizes = []
    for start in range(width * height):
        if not occupied[start] or seen[start]:
            continue
        seen[start] = 1
        stack = [start]
        size = 0
        while stack:
            point = stack.pop()
            size += 1
            x, y = point % width, point // width
            for neighbour in (
                point - 1 if x else -1,
                point + 1 if x + 1 < width else -1,
                point - width if y else -1,
                point + width if y + 1 < height else -1,
            ):
                if neighbour >= 0 and occupied[neighbour] and not seen[neighbour]:
                    seen[neighbour] = 1
                    stack.append(neighbour)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def has_split_mass(image):
    alpha = image.getchannel("A").resize((100, 100), Image.Resampling.BILINEAR)
    values = alpha.tobytes()
    columns = [0] * 100
    rows = [0] * 100
    for y in range(100):
        for x in range(100):
            columns[x] += values[y * 100 + x]
            rows[y] += values[y * 100 + x]

    def split(profile):
        peak = max(profile)
        if peak <= 0:
            return False
        occupied = peak * .06
        segments = []
        current = None
        gap = 0
        for value in profile:
            if value > occupied:
                if current is None:
                    segments.append(0)
                    current = len(segments) - 1
                segments[current] += value
                gap = 0
            elif current is not None:
                gap += 1
                if gap >= 5:
                    current = None
        if len(segments) < 2:
            return False
        segments.sort(reverse=True)
        return segments[1] >= segments[0] * .45

    return split(columns) or split(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--animations-dir", type=Path, required=True)
    parser.add_argument("--actions", default="all")
    parser.add_argument("--body-plan", choices=BODY_PLANS)
    parser.add_argument("--expected-frames", type=int, default=8)
    parser.add_argument("--min-distinct", type=int, default=6)
    parser.add_argument("--allow-split-mass", action="store_true")
    parser.add_argument("--allow-detached-components", action="store_true")
    parser.add_argument("--detached-min-pixels", type=int, default=8)
    parser.add_argument("--detached-min-ratio", type=float, default=.0001)
    parser.add_argument("--min-gutter", type=int, default=0)
    parser.add_argument("--display-scales", type=parse_display_scales, default={})
    parser.add_argument("--max-cross-action-scale-drift", type=float, default=.08)
    parser.add_argument("--allow-cross-action-scale-drift", action="store_true")
    args = parser.parse_args()

    if args.detached_min_pixels < 1:
        parser.error("detached min pixels must be positive")
    if not 0 <= args.detached_min_ratio <= 1:
        parser.error("detached min ratio must be between 0 and 1")
    if args.min_gutter < 0:
        parser.error("minimum gutter cannot be negative")
    if args.max_cross_action_scale_drift < 0:
        parser.error("cross-action scale drift cannot be negative")

    errors = []
    manifest_path = args.animations_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid manifest: {exc}")
        manifest = {}

    body_plan = args.body_plan or manifest.get("bodyPlan") or "quadruped"
    animations = {item.get("name"): item for item in manifest.get("animations", [])}
    actions = list(animations) if args.actions == "all" else names(args.actions)
    frame_size = int(manifest.get("frameSize", 512))
    airborne = BODY_PLANS[body_plan]["airborne"]
    action_diagonals = {}

    for action in actions:
        files = sorted((args.animations_dir / action).glob("frame-*.png"))
        if len(files) != args.expected_frames:
            errors.append(
                f"{action}: expected {args.expected_frames} frames, found {len(files)}"
            )
        hashes = set()
        boxes = []
        diagonals = []
        for file in files:
            try:
                with Image.open(file) as opened:
                    if opened.mode != "RGBA":
                        errors.append(f"{file}: mode is {opened.mode}, expected RGBA")
                    image = opened.convert("RGBA")
                    if image.size != (frame_size, frame_size):
                        errors.append(
                            f"{file}: size is {image.size}, expected {(frame_size, frame_size)}"
                        )
                    corners = ((0, 0), (frame_size - 1, 0), (0, frame_size - 1), (frame_size - 1, frame_size - 1))
                    if any(image.getpixel(point)[3] != 0 for point in corners):
                        errors.append(f"{file}: at least one corner is not transparent")
                    box = subject_bbox(image)
                    if not box:
                        errors.append(f"{file}: frame is empty")
                    else:
                        boxes.append(box)
                        diagonals.append(math.hypot(box[2] - box[0], box[3] - box[1]))
                        if args.min_gutter and min(
                            box[0], box[1], frame_size - box[2], frame_size - box[3]
                        ) < args.min_gutter:
                            errors.append(f"{file}: subject violates {args.min_gutter}px safe gutter")

                    edge = image.getchannel("A")
                    width, height = image.size
                    coverage = max(
                        sum(edge.getpixel((x, y)) > 24 for x in range(width))
                        for y in (0, height - 1)
                    ) / width
                    coverage = max(
                        coverage,
                        max(
                            sum(edge.getpixel((x, y)) > 24 for y in range(height))
                            for x in (0, width - 1)
                        ) / height,
                    )
                    if coverage > .7:
                        errors.append(f"{file}: likely residual frame border")
                    if not args.allow_split_mass and has_split_mass(image):
                        errors.append(f"{file}: possible duplicate/spillover sprite mass")

                    components = component_sizes(image)
                    if components and not args.allow_detached_components:
                        primary = components[0]
                        detached = [
                            size for size in components[1:]
                            if size >= args.detached_min_pixels
                            and size / primary >= args.detached_min_ratio
                        ]
                        if detached:
                            errors.append(
                                f"{file}: detached alpha components {detached} beside primary {primary}"
                            )
                    hashes.add(digest(image))
            except OSError as exc:
                errors.append(f"{file}: unreadable image: {exc}")

        if diagonals:
            action_diagonals[action] = median(diagonals)
        if len(hashes) < min(args.min_distinct, len(files)):
            errors.append(f"{action}: only {len(hashes)} distinct frames")
        if boxes and action not in airborne:
            bottoms = [box[3] for box in boxes]
            if max(bottoms) - min(bottoms) > 2:
                errors.append(
                    f"{action}: grounded baseline jitter is {max(bottoms) - min(bottoms)} px"
                )
        item = animations.get(action)
        if not item:
            errors.append(f"{action}: missing from manifest")
        elif item.get("frameCount") != len(files):
            errors.append(f"{action}: manifest frameCount mismatch")

    scale_group = [
        action for action in BODY_PLANS[body_plan].get("scale_group", [])
        if action in action_diagonals
    ]
    effective_sizes = {}
    for action in scale_group:
        item = animations.get(action) or {}
        scale = args.display_scales.get(action, float(item.get("displayScale", 1)))
        effective_sizes[action] = action_diagonals[action] * scale
    if len(effective_sizes) >= 2 and not args.allow_cross_action_scale_drift:
        reference = median(effective_sizes.values())
        for action, size in effective_sizes.items():
            drift = abs(size / reference - 1)
            if drift > args.max_cross_action_scale_drift:
                suggested = reference / action_diagonals[action]
                errors.append(
                    f"{action}: effective cross-action scale drift is {drift:.1%}; "
                    f"try display scale {suggested:.3f} and inspect transitions"
                )

    if errors:
        print("Animation validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"Animation validation passed: {body_plan}: {', '.join(actions)}")


if __name__ == "__main__":
    main()
