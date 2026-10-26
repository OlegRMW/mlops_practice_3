"""Create or resume three real ClearML datasets, then verify from a fresh cache."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from check_data import check_data
from prepare_data import prepare

ROOT = Path(__file__).resolve().parent
VERSIONS = {"BASE_ID": ("1.0.0", "base"), "WINE_ID": ("1.1.0", "wine"),
            "IRIS_FEATURES_ID": ("2.0.0", "iris_features")}


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def verify(registry: dict, downloads: Path, output: Path) -> None:
    # Imported after setting CLEARML_CACHE_DIR, in a separate process.
    from clearml import Dataset, Task

    result = {"project": registry["project"], "name": registry["name"],
              "ids": registry["ids"], "fresh_cache": os.environ["CLEARML_CACHE_DIR"],
              "versions": {}, "dependency_graph": {}}
    cache = Path(os.environ["CLEARML_CACHE_DIR"])
    if cache.exists() and any(cache.iterdir()):
        raise RuntimeError("Verification requires a fresh empty ClearML cache")
    for label, (version, state) in VERSIONS.items():
        dataset_id = registry["ids"][label]
        dataset = Dataset.get(dataset_id=dataset_id)
        assert dataset.id == dataset_id
        assert dataset.version == version
        assert dataset.project == registry["project"] and dataset.name == registry["name"]
        assert dataset.is_final()
        task = Task.get_task(task_id=dataset_id)
        assert str(task.status) == "completed", f"Unexpected dataset status: {task.status}"
        graph = dataset.get_dependency_graph()
        parents = graph[dataset_id]
        assert parents == ([] if label == "BASE_ID" else [registry["ids"]["BASE_ID"]])
        if label == "IRIS_FEATURES_ID":
            assert registry["ids"]["WINE_ID"] not in graph
        directory = downloads / version
        if directory.exists() and any(directory.iterdir()):
            raise RuntimeError(f"Download folder is not empty: {directory}")
        dataset.get_mutable_local_copy(target_folder=str(directory), overwrite=False)
        files = check_data(directory, state)
        assert sorted(dataset.list_files()) == sorted(p.name for p in directory.iterdir())
        expected_added = {"BASE_ID": ["iris.csv"], "WINE_ID": ["wine.csv"], "IRIS_FEATURES_ID": []}[label]
        expected_modified = ["iris.csv"] if label == "IRIS_FEATURES_ID" else []
        added = sorted(dataset.list_added_files())
        modified = sorted(dataset.list_modified_files())
        removed = sorted(dataset.list_removed_files())
        assert added == expected_added, (label, added)
        assert modified == expected_modified, (label, modified)
        assert removed == []
        owners = {name: entry.parent_dataset_id for name, entry in dataset.file_entries_dict.items()}
        if label == "WINE_ID":
            assert owners["iris.csv"] == registry["ids"]["BASE_ID"]
            assert owners["wine.csv"] == dataset_id
        record = {"dataset_id": dataset_id, "version": dataset.version, "parents": parents,
                  "status": str(task.status), "files": files, "all_files": sorted(dataset.list_files()),
                  "added": added, "modified": modified, "removed": removed,
                  "file_owner_dataset_ids": owners, "tags": task.get_tags(),
                  "ui_url": task.get_output_log_web_page(), "dependency_graph": graph}
        if label == "BASE_ID":
            assert "base" in record["tags"]
        result["versions"][label] = record
        result["dependency_graph"].update(graph)
    base = result["versions"]["BASE_ID"]["files"][0]
    assert result["versions"]["WINE_ID"]["files"][0] == base
    dvc_path = ROOT / "evidence/dvc.json"
    if dvc_path.exists():
        dvc = json.loads(dvc_path.read_text(encoding="utf-8"))
        for label, (_, state) in VERSIONS.items():
            assert result["versions"][label]["files"] == dvc[state]["files"]
        result["matches_dvc_versions"] = True
    save(output, result)
    print(f"Three completed versions downloaded by exact ID and verified: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surname")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--registry", type=Path, default=ROOT / "evidence/clearml_ids.json")
    parser.add_argument("--downloads", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/clearml.json")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(json.loads(args.registry.read_text(encoding="utf-8")), args.downloads, args.output)
        return
    if not args.surname or not re.fullmatch(r"[a-z][a-z0-9-]*", args.surname):
        parser.error("--surname must be a lowercase Latin surname")
    os.environ["CLEARML_CACHE_DIR"] = str(ROOT / ".runtime/clearml_creation_cache")
    from clearml import Dataset
    from clearml.backend_api import Session

    if Dataset.is_offline():
        parser.error("Offline ClearML mode does not satisfy the assignment")
    session = Session()
    api_server = session.get_api_server_host()
    print(f"Connected to ClearML API server: {api_server}")
    project = f"MIIT/MLOps/practice_3/{args.surname}"
    name = f"sklearn-tabular-{args.surname}"
    if args.registry.exists():
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
        assert registry["project"] == project and registry["name"] == name
        assert registry["api_server"] == api_server
    else:
        registry = {"project": project, "name": name, "api_server": api_server, "ids": {}}
    if not args.verify_only:
        source = ROOT / ".runtime/clearml_sources"
        for label, (version, state) in VERSIONS.items():
            directory = source / version
            if state == "wine":
                prepare("base", directory)
                prepare("wine", directory)
            else:
                prepare(state, directory)
            check_data(directory, state)
            if label in registry["ids"]:
                dataset = Dataset.get(dataset_id=registry["ids"][label])
                assert dataset.version == version and dataset.project == project and dataset.name == name
            else:
                dataset = Dataset.create(
                    dataset_project=project, dataset_name=name, dataset_version=version,
                    parent_datasets=None if label == "BASE_ID" else [registry["ids"]["BASE_ID"]],
                    dataset_tags=["practice-3", "base" if label == "BASE_ID" else state],
                    description={"BASE_ID": "Original sklearn Iris, deterministically sorted; no Wine.",
                                 "WINE_ID": "Adds Wine; original Iris inherited unchanged from the base.",
                                 "IRIS_FEATURES_ID": "Independent child of base: Iris with sepal_area and petal_area; no Wine."}[label],
                )
                # Persist real IDs immediately so interruption cannot cause accidental duplicates.
                registry["ids"][label] = dataset.id
                save(args.registry, registry)
            if not dataset.is_final():
                filename = "wine.csv" if label == "WINE_ID" else "iris.csv"
                dataset.add_files(path=str(directory / filename), local_base_folder=str(directory))
                dataset.upload()
                dataset.finalize()
            assert dataset.is_final()
            print(f"{label}={dataset.id} (version {version})", flush=True)
    if set(registry["ids"]) != set(VERSIONS):
        raise RuntimeError("All three real IDs are required for verification")
    run_dir = ROOT / ".runtime" / f"clearml_verify_{uuid4().hex}"
    run_dir.mkdir(parents=True)
    env = os.environ.copy()
    env["CLEARML_CACHE_DIR"] = str(run_dir / "fresh_cache")
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--verify",
                    "--registry", str(args.registry.resolve()), "--downloads", str(run_dir / "downloads"),
                    "--output", str(args.output.resolve())], cwd=ROOT, env=env, check=True)


if __name__ == "__main__":
    main()
