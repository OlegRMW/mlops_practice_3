"""Validate complete dataset states and print a JSON inventory with SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prepare_data import source_frame

STATES = {
    "base": {"iris.csv"},
    "wine": {"iris.csv", "wine.csv"},
    "iris_features": {"iris.csv"},
    "merged": {"iris.csv", "wine.csv"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_data(data_dir: Path = Path("data"), state: str = "merged") -> list[dict]:
    actual = {p.relative_to(data_dir).as_posix() for p in data_dir.rglob("*") if p.is_file()}
    if actual != STATES[state]:
        raise ValueError(f"File set mismatch: expected {sorted(STATES[state])}, got {sorted(actual)}")
    result = []
    for filename in sorted(actual):
        path = data_dir / filename
        frame = pd.read_csv(path, float_precision="round_trip")
        original = source_frame(path.stem)
        feature_mode = path.stem == "iris" and state in {"iris_features", "merged"}
        columns = list(original.columns) + (["sepal_area", "petal_area"] if feature_mode else [])
        if any(str(c).startswith("Unnamed:") for c in frame.columns):
            raise ValueError(f"{filename}: unexpected index column")
        if list(frame.columns) != columns or len(frame) != len(original):
            raise ValueError(f"{filename}: incorrect shape/column order: {frame.shape}, {list(frame.columns)}")
        if frame.isna().any().any():
            raise ValueError(f"{filename}: missing values")
        if not all(pd.api.types.is_numeric_dtype(t) for t in frame.dtypes):
            raise ValueError(f"{filename}: nonnumeric values")
        values = frame.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{filename}: nonfinite values")
        if not np.allclose(frame[list(original.columns)], original, rtol=1e-12, atol=1e-12):
            raise ValueError(f"{filename}: original values, targets or sorted row order changed")
        if not pd.api.types.is_integer_dtype(frame["target"].dtype):
            raise ValueError(f"{filename}: target must remain integer")
        if feature_mode:
            for area, length, width in [
                ("sepal_area", "sepal length (cm)", "sepal width (cm)"),
                ("petal_area", "petal length (cm)", "petal width (cm)"),
            ]:
                if not np.allclose(frame[area], frame[length] * frame[width], rtol=1e-12, atol=1e-12):
                    raise ValueError(f"{filename}: wrong values in {area}")
        result.append({
            "path": f"data/{filename}", "sha256": sha256(path),
            "rows": len(frame), "columns_count": len(frame.columns),
            "columns": list(frame.columns), "dtypes": {c: str(t) for c, t in frame.dtypes.items()},
            "missing_values": int(frame.isna().sum().sum()),
            "first_row": frame.iloc[0].to_dict(), "last_row": frame.iloc[-1].to_dict(),
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=STATES, default="merged")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = check_data(args.data_dir, args.state)
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        parser.exit(1, f"Validation failed: {exc}\n")
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
