#!/usr/bin/env python3
"""Launch the newest current-OS desktop-pet build and leave it running."""

from __future__ import annotations

import argparse
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path


def newest(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    return max(existing, key=lambda path: path.stat().st_mtime, default=None)


def top_level_apps(dist: Path) -> list[Path]:
    return [
        path
        for path in dist.rglob("*.app")
        if not any(parent.suffix.lower() == ".app" for parent in path.parents)
    ]


def discover_artifact(project: Path, system: str) -> Path | None:
    dist = project / "dist"
    if not dist.is_dir():
        return None
    if system == "Darwin":
        return newest(top_level_apps(dist))
    if system == "Windows":
        ignored = {"crashpad_handler.exe", "elevate.exe", "ffmpeg.exe", "squirrel.exe", "update.exe"}
        candidates = [
            path
            for path in dist.rglob("*.exe")
            if path.name.lower() not in ignored and "uninstall" not in path.name.lower()
        ]
        return newest(candidates)
    if system == "Linux":
        return newest(list(dist.rglob("*.AppImage")) + list(dist.rglob("*.appimage")))
    return None


def mac_executable(app_bundle: Path) -> Path:
    info = app_bundle / "Contents" / "Info.plist"
    try:
        with info.open("rb") as handle:
            executable = plistlib.load(handle)["CFBundleExecutable"]
    except (OSError, KeyError, plistlib.InvalidFileException) as exc:
        raise RuntimeError(f"cannot read macOS bundle executable from {info}: {exc}") from exc
    target = app_bundle / "Contents" / "MacOS" / executable
    if not target.is_file():
        raise RuntimeError(f"macOS bundle executable is missing: {target}")
    return target.resolve()


def posix_processes() -> list[tuple[int, str]]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    processes: list[tuple[int, str]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        processes.append((int(parts[0]), parts[1]))
    return processes


def find_posix_pids(signature: str) -> list[int]:
    return [pid for pid, command in posix_processes() if signature in command and pid != os.getpid()]


def find_windows_pids(executable: Path) -> list[int]:
    escaped = str(executable.resolve()).replace("'", "''")
    command = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.ExecutablePath -eq '{escaped}' }} | "
        "Select-Object -ExpandProperty ProcessId"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )
    return [int(line) for line in result.stdout.splitlines() if line.strip().isdigit()]


def wait_for_pids(finder, timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pids = finder()
        if pids:
            return pids
        time.sleep(0.25)
    return []


def launch_packaged(artifact: Path, system: str, wait_seconds: float) -> tuple[str, list[int]]:
    if system == "Darwin":
        if artifact.suffix.lower() != ".app":
            raise RuntimeError(f"expected a .app bundle on macOS, got: {artifact}")
        executable = mac_executable(artifact)
        finder = lambda: find_posix_pids(str(executable))
        existing = finder()
        if existing:
            return "already-running", existing
        result = subprocess.run(["open", "-n", str(artifact)], check=False, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"open failed with exit code {result.returncode}")
        pids = wait_for_pids(finder, wait_seconds)
        if not pids:
            raise RuntimeError(f"the app did not remain running for {wait_seconds:g}s: {artifact}")
        return "launched", pids

    if system == "Windows":
        if artifact.suffix.lower() != ".exe":
            raise RuntimeError(f"expected an .exe on Windows, got: {artifact}")
        finder = lambda: find_windows_pids(artifact)
        existing = finder()
        if existing:
            return "already-running", existing
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        process = subprocess.Popen(
            [str(artifact)],
            cwd=artifact.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        pids = wait_for_pids(finder, wait_seconds)
        if not pids or process.poll() is not None:
            raise RuntimeError(f"the app exited during the {wait_seconds:g}s launch check: {artifact}")
        return "launched", pids

    if system == "Linux":
        executable = artifact.resolve()
        signature = str(executable)
        finder = lambda: find_posix_pids(signature)
        existing = finder()
        if existing:
            return "already-running", existing
        process = subprocess.Popen(
            [signature],
            cwd=artifact.parent,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(wait_seconds)
        if process.poll() is not None:
            raise RuntimeError(f"the app exited during the {wait_seconds:g}s launch check: {artifact}")
        return "launched", [process.pid]

    raise RuntimeError(f"unsupported operating system: {system}")


def launch_dev(project: Path, system: str, wait_seconds: float) -> tuple[str, list[int]]:
    if not (project / "package.json").is_file():
        raise RuntimeError(f"no current-OS package or package.json found under {project}")
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required for the development-runtime fallback")
    kwargs: dict[str, object] = {
        "cwd": project,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if system == "Windows":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen([npm, "start"], **kwargs)
    time.sleep(wait_seconds)
    if process.poll() is not None:
        raise RuntimeError(f"npm start exited during the {wait_seconds:g}s launch check")
    return "launched-dev", [process.pid]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, help="explicit current-OS .app, .exe, or AppImage")
    parser.add_argument("--dev", action="store_true", help="force the npm start fallback")
    parser.add_argument("--wait-seconds", type=float, default=3.0)
    args = parser.parse_args()
    if args.wait_seconds < 1:
        parser.error("--wait-seconds must be at least 1")
    return args


def main() -> int:
    args = parse_args()
    project = args.project_dir.expanduser().resolve()
    if not project.is_dir():
        raise RuntimeError(f"project directory does not exist: {project}")
    system = platform.system()
    artifact = None if args.dev else args.artifact
    if artifact is not None:
        artifact = artifact.expanduser().resolve()
        if not artifact.exists():
            raise RuntimeError(f"artifact does not exist: {artifact}")
    if artifact is None and not args.dev:
        artifact = discover_artifact(project, system)

    if artifact is None:
        status, pids = launch_dev(project, system, args.wait_seconds)
        target = project
    else:
        status, pids = launch_packaged(artifact, system, args.wait_seconds)
        target = artifact
    print(f"RUNNING status={status} pids={','.join(map(str, pids))} target={target}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"LAUNCH_FAILED {exc}", file=sys.stderr)
        sys.exit(1)
