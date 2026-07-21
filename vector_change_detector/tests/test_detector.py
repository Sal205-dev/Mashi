from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from vector_change_detector.core.detector import ChangeType, detect_changes
from vector_change_detector.core.matcher import match_datasets


def _square(x0: float, y0: float, size: float) -> Polygon:
    return Polygon(
        [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size), (x0, y0)]
    )


def test_detect_changes_classifies_all_categories():
    reference = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[_square(0, 0, 10), _square(100, 0, 10), _square(200, 0, 10)],
        crs="EPSG:4326",
    )
    compare = gpd.GeoDataFrame(
        {"id": [1, 3, 4]},
        geometry=[_square(0, 0, 10), _square(200, 0, 5), _square(300, 0, 10)],
        crs="EPSG:4326",
    )

    matches = match_datasets(reference, compare)
    results = detect_changes(reference, compare, matches, unchanged_iou_threshold=0.90)

    assert len(results) == 4
    assert set(results["change_type"]) == {
        ChangeType.UNCHANGED.value,
        ChangeType.DELETED.value,
        ChangeType.MODIFIED.value,
        ChangeType.ADDED.value,
    }

    added = results.loc[results["change_type"] == ChangeType.ADDED.value].iloc[0]
    assert added["old_area"] == 0.0
    assert added["new_area"] == 100.0
    assert pd.isna(added["pct_change"])

    deleted = results.loc[results["change_type"] == ChangeType.DELETED.value].iloc[0]
    assert deleted["new_area"] == 0.0
    assert deleted["old_area"] == 100.0

    modified = results.loc[results["change_type"] == ChangeType.MODIFIED.value].iloc[0]
    assert modified["area_diff"] < 0
    assert modified["pct_change"] == -75.0

    unchanged = results.loc[results["change_type"] == ChangeType.UNCHANGED.value].iloc[0]
    assert unchanged["area_diff"] == 0.0


def test_unchanged_iou_threshold_controls_modified_vs_unchanged_boundary():
    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")
    compare = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 9.5)], crs="EPSG:4326")

    matches = match_datasets(reference, compare)

    strict = detect_changes(reference, compare, matches, unchanged_iou_threshold=0.99)
    assert strict.iloc[0]["change_type"] == ChangeType.MODIFIED.value

    lenient = detect_changes(reference, compare, matches, unchanged_iou_threshold=0.50)
    assert lenient.iloc[0]["change_type"] == ChangeType.UNCHANGED.value
