#!/usr/bin/env python3
"""Copy the bundled transparent Electron desktop-pet template."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="overwrite matching template files")
    args = parser.parse_args()
    template = Path(__file__).resolve().parents[1] / "assets" / "electron-template"
    if not template.is_dir():
        parser.error(f"template not found: {template}")
    files = [path for path in template.rglob("*") if path.is_file()]
    conflicts = [args.output_dir / path.relative_to(template) for path in files if (args.output_dir / path.relative_to(template)).exists()]
    if conflicts and not args.force:
        names = "\n".join(f"- {path}" for path in conflicts)
        parser.error(f"refusing to overwrite existing files:\n{names}\nUse --force to replace them.")
    for source in files:
        target = args.output_dir / source.relative_to(template)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print(target)


if __name__ == "__main__":
    main()
