"""Execute the DVC exercise once in this repository; retain measured evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from check_data import check_data
from prepare_data import prepare
from git_runtime import ensure_safe_directory

ROOT = Path(__file__).resolve().parent


def run(*command: str, cwd: Path = ROOT) -> str:
    process = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"$ {' '.join(command)}\n{process.stdout}", flush=True)
    if process.returncode:
        raise RuntimeError(f"Command exited {process.returncode}: {command[0:3]}")
    return process.stdout.strip()


def dvc(*args: str, cwd: Path = ROOT) -> str:
    return run(sys.executable, "-m", "dvc", *args, cwd=cwd)


def git(*args: str, cwd: Path = ROOT) -> str:
    ensure_safe_directory(cwd)
    return run("git", *args, cwd=cwd)


def snapshot(state: str, cwd: Path = ROOT) -> dict:
    status = json.loads(dvc("status", "--json", cwd=cwd))
    if status:
        raise AssertionError(f"Uncommitted DVC data: {status}")
    return {
        "commit": git("rev-parse", "HEAD", cwd=cwd),
        "data_dvc_sha256": hashlib.sha256((cwd / "data.dvc").read_bytes()).hexdigest(),
        "data_dvc": (cwd / "data.dvc").read_text(encoding="utf-8"),
        "files": check_data(cwd / "data", state), "dvc_status": status,
    }


def commit(message: str, *files: str) -> str:
    git("add", "--", *files)
    git("commit", "-m", message)
    return git("rev-parse", "HEAD")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surname", required=True)
    parser.add_argument("--repository-url", required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Python 3.12 is required")
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.surname):
        parser.error("Use a lowercase Latin surname")
    if ROOT.name != f"mlops-data-{args.surname}":
        parser.error(f"Repository must be named mlops-data-{args.surname}")
    if (ROOT / "data").exists():
        parser.error("Data already exists; refusing to overwrite an interrupted data experiment")
    if (ROOT / ".git").exists():
        ensure_safe_directory(ROOT)
        head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT, capture_output=True)
        refs = subprocess.run(["git", "show-ref"], cwd=ROOT, capture_output=True)
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
        initial_dvc_files = {".dvc/.gitignore", ".dvc/config", ".dvcignore"}
        if head.returncode == 0 or refs.returncode != 1 or not set(tracked.splitlines()).issubset(initial_dvc_files):
            parser.error("Existing Git history or noninitial index found; refusing to overwrite. Only DVC initialization can be resumed")
    if not (ROOT / "poetry.lock").is_file():
        parser.error("Run poetry lock first")
    run(sys.executable, "-m", "poetry", "check", "--lock")
    for package, expected in {"dvc": "3.63.0", "clearml": "2.0.2", "scikit-learn": "1.7.2", "pandas": "2.3.3", "pathspec": "0.12.1"}.items():
        if importlib.metadata.version(package) != expected:
            parser.error(f"Install pinned dependency {package}=={expected}")
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    os.environ["DVC_NO_ANALYTICS"] = "1"
    os.environ["DVC_SITE_CACHE_DIR"] = str(ROOT / ".runtime/dvc_site_cache")
    remote = ROOT.parent / f"dvc-remote-{args.surname}"
    clone = ROOT.parent / f"clean-clone-{args.surname}"
    if clone.exists() or (remote.exists() and (not remote.is_dir() or any(remote.iterdir()))):
        parser.error("Clone target or nonempty remote already exists; refusing to reuse old data")
    remote.mkdir(exist_ok=True)
    git("init", "-b", "main")
    if git("symbolic-ref", "--short", "HEAD") != "main":
        parser.error("Empty repository is not on main; refusing to change its branch implicitly")
    git("config", "core.autocrlf", "false")
    git("config", "merge.dvc.name", "DVC merge driver")
    git("config", "merge.dvc.driver", "dvc git-hook merge-driver --ancestor %O --our %A --their %B")
    if "origin" in git("remote").splitlines():
        if git("remote", "get-url", "origin") != args.repository_url:
            parser.error("Existing origin differs from the requested repository")
    else:
        git("remote", "add", "origin", args.repository_url)
    if not (ROOT / ".dvc/config").exists():
        dvc("init")
    else:
        dvc("status")
    dvc("config", "core.analytics", "false")
    dvc("config", "cache.type", "copy")
    # ConfigObj used by this DVC version writes ASCII. A relative URL avoids
    # embedding the Cyrillic workspace prefix and remains valid in the sibling clone.
    remote_url = Path(os.path.relpath(remote, ROOT)).as_posix()
    dvc("remote", "add", "--force", "-d", "storage", remote_url)
    prepare("base", ROOT / "data")
    check_data(ROOT / "data", "base")
    dvc("add", "data")
    commit("Track deterministic Iris base with DVC and pinned environment", ".")
    git("tag", "data-v1")
    dvc("push")
    evidence = {
        "surname": args.surname, "repository_url": args.repository_url,
        "python": sys.version.split()[0],
        "packages": {p: importlib.metadata.version(p) for p in ["dvc", "clearml", "scikit-learn", "pandas", "numpy", "poetry", "pathspec"]},
        "remote": remote.as_posix(), "remote_url_argument": remote_url, "base": snapshot("base"),
    }
    git("switch", "-c", "feature/wine")
    prepare("wine", ROOT / "data")
    dvc("add", "data")
    commit("Add Wine without changing Iris", "data.dvc")
    git("tag", "data-wine")
    dvc("push")
    evidence["wine"] = snapshot("wine")
    assert evidence["wine"]["files"][0]["sha256"] == evidence["base"]["files"][0]["sha256"]
    git("switch", "main")
    evidence["stale_workspace_after_git_switch"] = {
        "wine_still_exists": (ROOT / "data/wine.csv").exists(),
        "dvc_status": json.loads(dvc("status", "--json")),
    }
    dvc("checkout")
    assert check_data(ROOT / "data", "base") == evidence["base"]["files"]
    evidence["main_restored_after_checkout"] = True
    git("switch", "-c", "feature/iris-features")
    prepare("iris_features", ROOT / "data")
    dvc("add", "data")
    commit("Add sepal_area and petal_area on independent Iris branch", "data.dvc")
    git("tag", "data-iris-features")
    dvc("push")
    evidence["iris_features"] = snapshot("iris_features")
    merge_output = git("merge", "--no-ff", "feature/wine", "-m", "Merge Wine addition with Iris feature changes through DVC driver")
    assert "<<<<<<<" not in (ROOT / "data.dvc").read_text(encoding="utf-8")
    dvc("checkout")
    merged = check_data(ROOT / "data", "merged")
    assert merged[0] == evidence["iris_features"]["files"][0]
    assert merged[1] == evidence["wine"]["files"][1]
    evidence["merge"] = {"commit": git("rev-parse", "HEAD"),
                          "parents": git("show", "-s", "--format=%P", "HEAD").split(),
                          "automatic_driver_success": True, "summary": merge_output}
    assert len(evidence["merge"]["parents"]) == 2
    git("switch", "main")
    git("merge", "--ff-only", "feature/iris-features")
    dvc("checkout")
    dvc("push")
    git("tag", "data-merged")
    evidence["merged"] = snapshot("merged")
    tracked = git("ls-files").splitlines()
    assert not any(p.endswith(".csv") or p.startswith(("data/", ".dvc/cache/")) for p in tracked)
    evidence["no_data_in_git"] = True
    evidence["remote_status"] = json.loads(dvc("status", "--cloud", "--json"))
    assert not evidence["remote_status"]
    git("clone", "--no-local", str(ROOT), str(clone), cwd=ROOT.parent)
    assert not (clone / "data").exists()
    assert not (clone / ".dvc/cache").exists()
    dvc("pull", cwd=clone)
    restored = snapshot("merged", clone)
    assert restored["files"] == evidence["merged"]["files"]
    evidence["clean_clone"] = {"path": clone.as_posix(), "initially_empty_cache": True,
                               "files": restored["files"], "hashes_match": True}
    # Independently pull every historical state with an initially fresh clone cache.
    evidence["historical_restore"] = {}
    for tag, state in [("data-v1", "base"), ("data-wine", "wine"), ("data-iris-features", "iris_features")]:
        git("switch", "--detach", tag, cwd=clone)
        dvc("pull", cwd=clone)
        restored = snapshot(state, clone)
        assert restored["files"] == evidence[state]["files"]
        evidence["historical_restore"][tag] = restored
    git("switch", "main", cwd=clone)
    dvc("pull", cwd=clone)
    output = ROOT / "evidence/dvc.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"DVC exercise verified; evidence: {output}")


if __name__ == "__main__":
    main()
