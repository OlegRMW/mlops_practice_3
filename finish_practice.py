"""Finish real DVC/ClearML runs, build the report and optionally push Git refs."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from git_runtime import ensure_safe_directory

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--surname", default="zagudaev")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()
    os.chdir(ROOT)
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    os.environ["DVC_SITE_CACHE_DIR"] = str(ROOT / ".runtime/dvc_site_cache")
    os.environ["DVC_NO_ANALYTICS"] = "1"
    def run(*command):
        subprocess.run(command, cwd=ROOT, check=True)
    def script(name, *parameters):
        run(sys.executable, str(ROOT / name), *parameters)
    run(sys.executable, "-m", "unittest", "-v", "test_data")
    if not (ROOT / "evidence/dvc.json").exists():
        script("run_dvc_practice.py", "--surname", args.surname, "--repository-url", args.repository_url)
    else:
        ensure_safe_directory(ROOT)
        run("git", "remote", "set-url", "origin", args.repository_url)
    if not (ROOT / "evidence/clearml.json").exists():
        script("run_clearml_practice.py", "--surname", args.surname)
    import json
    dvc_evidence = json.loads((ROOT / "evidence/dvc.json").read_text(encoding="utf-8"))
    clearml_path = ROOT / "evidence/clearml.json"
    clearml_evidence = json.loads(clearml_path.read_text(encoding="utf-8"))
    for label, state in [("BASE_ID", "base"), ("WINE_ID", "wine"), ("IRIS_FEATURES_ID", "iris_features")]:
        if clearml_evidence["versions"][label]["files"] != dvc_evidence[state]["files"]:
            raise RuntimeError(f"ClearML/DVC contents differ: {label}")
    clearml_evidence["matches_dvc_versions"] = True
    clearml_path.write_text(json.dumps(clearml_evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    demo_path = ROOT / "evidence/demo.json"
    if not demo_path.exists() or not json.loads(demo_path.read_text(encoding="utf-8"))["clearml_executed"]:
        script("run_demo.py", "--surname", args.surname, "--clearml")
    script("build_report.py", "--require-complete")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    if any(p.endswith(".csv") or p.startswith(("data/", ".runtime/", ".dvc/cache/"))
           or p.rsplit("/", 1)[-1] in {"clearml.conf", ".env", ".session.json"} for p in tracked):
        raise RuntimeError("Unexpected local data/cache/config tracked by Git")
    run("git", "add", "--", "REPORT.md", "README.md", "evidence", "finish_practice.py", "build_report.py", "run_demo.py", "run_clearml_practice.py", "run_dvc_practice.py", "git_runtime.py")
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if changed.returncode == 1:
        run("git", "commit", "-m", "Document verified DVC restores and completed ClearML lineage")
    elif changed.returncode:
        raise RuntimeError("Unable to inspect staged changes")
    if args.push:
        run("git", "push", "-u", "origin", "main", "feature/wine", "feature/iris-features")
        run("git", "push", "origin", "--tags")
    print("Practice complete. Report: " + str(ROOT / "REPORT.md"))


if __name__ == "__main__":
    main()
