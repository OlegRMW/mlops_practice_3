"""Execute the supplied teaching notebook without needing a network kernel."""
from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from git_runtime import ensure_safe_directory

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surname", required=True)
    parser.add_argument("--clearml", action="store_true")
    args = parser.parse_args()
    notebook = json.loads((ROOT / "demo.ipynb").read_text(encoding="utf-8"))
    run_root = ROOT / ".runtime" / f"demo_{uuid4().hex}"
    run_root.mkdir(parents=True)
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    os.environ["DVC_NO_ANALYTICS"] = "1"
    os.environ["DVC_SITE_CACHE_DIR"] = str(run_root / "dvc_site_cache")
    os.environ["CLEARML_CACHE_DIR"] = str(run_root / "clearml_cache")
    original_cwd = Path.cwd()
    os.chdir(run_root)
    namespace = {"__name__": "__main__", "os": os}
    notebook_run = None

    def shared_directory_run(command, cwd):
        ensure_safe_directory(Path(cwd))
        result = notebook_run(command, cwd)
        ensure_safe_directory(Path(cwd))
        return result
    count = 0
    try:
        for cell in notebook["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"])
            source = source.replace("str(dvc_remote.resolve())", "os.path.relpath(dvc_remote.resolve(), dvc_repo.resolve())")
            if 'student_id = "replace-with-your-id"' in source:
                source = source.replace("run_clearml = False", f"run_clearml = {args.clearml!r}")
                source = source.replace('student_id = "replace-with-your-id"', f"student_id = {args.surname!r}")
            cell["source"] = source.splitlines(keepends=True)
            count += 1
            print(f"Executing demo cell {count}", flush=True)
            buffer = io.StringIO()
            outputs = []

            def display(value):
                data = {"text/plain": repr(value)}
                if hasattr(value, "_repr_html_"):
                    html = value._repr_html_()
                    if html:
                        data["text/html"] = html
                outputs.append({"output_type": "display_data", "data": data, "metadata": {}})

            tree = ast.parse(source)
            last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
            try:
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                    exec(compile(tree, f"demo-cell-{count}", "exec"), namespace)
                    if notebook_run is None and "run" in namespace:
                        notebook_run = namespace["run"]
                        namespace["run"] = shared_directory_run
                    namespace["display"] = display
                    if last is not None:
                        value = eval(compile(ast.Expression(last.value), f"demo-cell-{count}", "eval"), namespace)
                        if value is not None:
                            display(value)
            except subprocess.CalledProcessError as exc:
                print(exc.stdout or "", exc.stderr or "", flush=True)
                raise
            if buffer.getvalue():
                outputs.insert(0, {"output_type": "stream", "name": "stdout", "text": buffer.getvalue().splitlines(keepends=True)})
            cell["execution_count"] = count
            cell["outputs"] = outputs
        source = namespace["source_dir"]
        clone_data = namespace["dvc_clone"] / "data"
        hashes = {}
        for name in ["digits.csv", "diabetes.csv"]:
            digest = namespace["sha256_file"](clone_data / name)
            assert digest == namespace["sha256_file"](source / name)
            hashes[name] = digest
        evidence = {"executed_code_cells": count, "clearml_executed": args.clearml,
                    "clean_clone_hashes_match": True, "files": hashes,
                    "base_commit": namespace["base_commit"], "second_commit": namespace["second_commit"]}
        if args.clearml:
            evidence["BASE_ID"] = namespace["base_id"]
            evidence["CHILD_ID"] = namespace["child_id"]
            assert namespace["base_dataset"].is_final() and namespace["child_dataset"].is_final()
    finally:
        os.chdir(original_cwd)
    output = ROOT / "evidence"
    output.mkdir(exist_ok=True)
    (output / "demo.executed.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (output / "demo.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Teaching notebook completed: {count} code cells. ClearML enabled: {args.clearml}")


if __name__ == "__main__":
    main()
