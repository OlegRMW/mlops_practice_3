"""Acceptance checks for reproducibility and rejection of corrupted CSVs."""
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from check_data import check_data, sha256
from prepare_data import prepare


class DataAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"

    def test_determinism_and_modes(self):
        iris = prepare("base", self.data)
        base_hash = sha256(iris)
        prepare("base", self.data)
        self.assertEqual(base_hash, sha256(iris))
        check_data(self.data, "base")
        wine = prepare("wine", self.data)
        self.assertEqual(base_hash, sha256(iris))
        wine_hash = sha256(wine)
        prepare("wine", self.data)
        self.assertEqual(wine_hash, sha256(wine))
        check_data(self.data, "wine")
        prepare("iris_features", self.data)
        feature_hash = sha256(iris)
        prepare("iris_features", self.data)
        self.assertEqual(feature_hash, sha256(iris))
        self.assertEqual(wine_hash, sha256(wine))
        self.assertNotEqual(base_hash, feature_hash)
        check_data(self.data, "merged")
        self.assertNotIn(b"\r", iris.read_bytes())

    def test_feature_branch_has_no_wine(self):
        prepare("iris_features", self.data)
        check_data(self.data, "iris_features")

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            check_data(self.data, "base")

    def test_reject_corruptions(self):
        for damage in ["index", "rows", "area", "target", "missing", "order", "extra", "infinity"]:
            with self.subTest(damage=damage):
                path = prepare("iris_features", self.data)
                frame = pd.read_csv(path)
                if damage == "rows": frame = frame.iloc[:-1]
                elif damage == "area": frame.loc[0, "petal_area"] = -1
                elif damage == "target": frame.loc[0, "target"] = 9
                elif damage == "missing": frame.loc[0, "sepal_area"] = float("nan")
                elif damage == "order": frame = frame.iloc[::-1]
                elif damage == "extra": frame["unexpected"] = 0
                elif damage == "infinity": frame.loc[0, "sepal_area"] = float("inf")
                frame.to_csv(path, index=(damage == "index"))
                with self.assertRaises(ValueError):
                    check_data(self.data, "iris_features")


if __name__ == "__main__":
    unittest.main()
