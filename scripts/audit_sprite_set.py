#!/usr/bin/env python3
"""Report cross-action visual scale, baselines, gutters, and detached fragments."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image

from sprite_methods import BODY_PLANS
from validate_animations import component_sizes, names, parse_display_scales, subject_bbox


def clamp(value, low=.75, high=1.35):
    return max(low, min(high, value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--animations-dir", type=Path, required=True)
    parser.add_argument("--actions", default="all")
    parser.add_argument("--reference-action")
    parser.add_argument("--display-scales", type=parse_display_scales, default={})
    parser.add_argument("--write-manifest", action="store_true", help="persist explicitly supplied display scales")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    manifest = json.loads((args.animations_dir / "manifest.json").read_text(encoding="utf-8"))
    body_plan = manifest.get("bodyPlan", "quadruped")
    animations = {item["name"]: item for item in manifest.get("animations", [])}
    actions = list(animations) if args.actions == "all" else names(args.actions)
    missing = [action for action in actions if action not in animations]
    if missing:
        parser.error(f"actions missing from manifest: {', '.join(missing)}")

    rows = []
    for action in actions:
        widths = []
        heights = []
        diagonals = []
        masses = []
        bottoms = []
        gutters = []
        detached = 0
        for path in sorted((args.animations_dir / action).glob("frame-*.png")):
            image = Image.open(path).convert("RGBA")
            box = subject_bbox(image)
            if not box:
                continue
            width = box[2] - box[0]
            height = box[3] - box[1]
            widths.append(width)
            heights.append(height)
            diagonals.append(math.hypot(width, height))
            masses.append(math.sqrt(sum(value > 48 for value in image.getchannel("A").getdata())))
            bottoms.append(box[3])
            gutters.append(min(box[0], box[1], image.width - box[2], image.height - box[3]))
            sizes = component_sizes(image)
            detached += max(0, len([size for size in sizes[1:] if size >= 8]))

        if not diagonals:
            parser.error(f"no non-empty frames found for action: {action}")

        item = animations[action]
        display_scale = args.display_scales.get(action, float(item.get("displayScale", 1)))
        rows.append({
            "action": action,
            "medianWidth": median(widths),
            "medianHeight": median(heights),
            "medianDiagonal": median(diagonals),
            "medianMassExtent": median(masses),
            "displayScale": display_scale,
            "effectiveDiagonal": median(diagonals) * display_scale,
            "baselineRange": max(bottoms) - min(bottoms),
            "minimumGutter": min(gutters),
            "detachedComponents": detached,
        })

    available = {row["action"] for row in rows}
    reference_action = args.reference_action
    if not reference_action:
        candidates = ["walk", BODY_PLANS[body_plan]["default"], *actions]
        reference_action = next(candidate for candidate in candidates if candidate in available)
    if reference_action not in available:
        parser.error(f"reference action not audited: {reference_action}")
    reference = next(row for row in rows if row["action"] == reference_action)
    target_diagonal = reference["effectiveDiagonal"]
    target_mass = reference["medianMassExtent"] * reference["displayScale"]
    for row in rows:
        row["recommendedDiagonalScale"] = clamp(target_diagonal / row["medianDiagonal"])
        row["recommendedMassScale"] = clamp(target_mass / row["medianMassExtent"])

    print(
        "action       diag   mass  shown  effective  rec-diag  rec-mass  "
        "baseΔ  gutter  fragments"
    )
    for row in rows:
        print(
            f"{row['action']:<11} {row['medianDiagonal']:>6.1f} "
            f"{row['medianMassExtent']:>6.1f} {row['displayScale']:>6.3f} "
            f"{row['effectiveDiagonal']:>9.1f} "
            f"{row['recommendedDiagonalScale']:>8.3f} "
            f"{row['recommendedMassScale']:>8.3f} "
            f"{row['baselineRange']:>6} {row['minimumGutter']:>7} "
            f"{row['detachedComponents']:>10}"
        )
    print(f"reference action: {reference_action}")

    payload = {"bodyPlan": body_plan, "referenceAction": reference_action, "actions": rows}
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.write_manifest:
        if not args.display_scales:
            parser.error("--write-manifest requires explicit --display-scales")
        unknown = sorted(set(args.display_scales) - set(animations))
        if unknown:
            parser.error(f"display scales reference unknown actions: {', '.join(unknown)}")
        for action, scale in args.display_scales.items():
            animations[action]["displayScale"] = scale
        (args.animations_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"updated displayScale values in {args.animations_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
