"""Deterministic sklearn CSV export. Each mode writes exactly one file."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.datasets import load_iris, load_wine

CSV_OPTIONS = dict(index=False, encoding="utf-8", lineterminator="\n", float_format="%.15g")


def source_frame(name: str) -> pd.DataFrame:
    frame = {"iris": load_iris, "wine": load_wine}[name](as_frame=True).frame
    return frame.sort_values(list(frame.columns), kind="mergesort").reset_index(drop=True)


def prepare(mode: str, data_dir: Path = Path("data")) -> Path:
    name = "wine" if mode == "wine" else "iris"
    frame = source_frame(name)
    if mode == "iris_features":
        frame["sepal_area"] = frame["sepal length (cm)"] * frame["sepal width (cm)"]
        frame["petal_area"] = frame["petal length (cm)"] * frame["petal width (cm)"]
    elif mode not in {"base", "wine"}:
        raise ValueError(f"Unknown mode: {mode}")
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / f"{name}.csv"
    # newline="" prevents Windows from converting LF to CRLF.
    with output.open("w", encoding="utf-8", newline="") as stream:
        frame.to_csv(stream, **CSV_OPTIONS)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["base", "wine", "iris_features"])
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(prepare(args.mode, args.data_dir))


if __name__ == "__main__":
    main()
