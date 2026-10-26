"""Trust only known exercise repositories when Windows account ownership differs."""
from __future__ import annotations

from pathlib import Path
import subprocess


def ensure_safe_directory(directory: Path) -> None:
    directory = directory.resolve()
    if not (directory / ".git").exists():
        return
    probe = subprocess.run(["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    if probe.returncode == 0:
        return
    if "dubious ownership" not in probe.stderr:
        raise RuntimeError(f"Cannot open Git repository {directory}: {probe.stderr}")
    # This exact exercise directory is intentionally shared by Codex and the
    # user's Windows account. Never use a wildcard exception.
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", directory.as_posix()], check=True)
    subprocess.run(["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                   check=True, stdout=subprocess.DEVNULL)
    print(f"Configured Git safe.directory for shared exercise directory: {directory}", flush=True)
