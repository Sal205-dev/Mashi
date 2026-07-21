from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from vector_change_detector.core.detector import ChangeType
from vector_change_detector.core.exporter import (
    export_category_layers,
    export_changes_layer,
    export_overall_summary,
    export_summary_csv,
)


def _make_results_gdf() -> gpd.GeoDataFrame:
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    return gpd.GeoDataFrame(
        {
            "change_id": ["a", "b", "c", "d"],
            "change_type": [
                ChangeType.ADDED.value,
                ChangeType.DELETED.value,
                ChangeType.MODIFIED.value,
                ChangeType.UNCHANGED.value,
            ],
            "old_area_sqkm": [0.0, 1.0, 1.0, 1.0],
            "new_area_sqkm": [1.0, 0.0, 0.5, 1.0],
            "area_diff_sqkm": [1.0, -1.0, -0.5, 0.0],
        },
        geometry=[square, square, square, square],
        crs="EPSG:4326",
    )


def test_export_category_layers_writes_one_file_per_category(tmp_path: Path):
    results = _make_results_gdf()

    export_category_layers(results, tmp_path)

    assert (tmp_path / "Added.geojson").exists()
    assert (tmp_path / "Deleted.geojson").exists()
    assert (tmp_path / "Modified.geojson").exists()

    with open(tmp_path / "Added.geojson") as f:
        added = json.load(f)
    assert len(added["features"]) == 1


def test_export_category_layers_writes_empty_featurecollection_when_no_matches(tmp_path: Path):
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    results = gpd.GeoDataFrame(
        {
            "change_id": ["a"],
            "change_type": [ChangeType.UNCHANGED.value],
            "old_area_sqkm": [1.0],
            "new_area_sqkm": [1.0],
            "area_diff_sqkm": [0.0],
        },
        geometry=[square],
        crs="EPSG:4326",
    )

    export_category_layers(results, tmp_path)

    with open(tmp_path / "Added.geojson") as f:
        added = json.load(f)
    assert added == {"type": "FeatureCollection", "features": []}


def test_export_changes_layer_excludes_unchanged(tmp_path: Path):
    results = _make_results_gdf()

    export_changes_layer(results, tmp_path)

    with open(tmp_path / "Changes.geojson") as f:
        changes = json.load(f)
    assert len(changes["features"]) == 3


def test_export_summary_csv_has_row_per_change_type(tmp_path: Path):
    results = _make_results_gdf()

    summary = export_summary_csv(results, tmp_path)

    assert (tmp_path / "Summary.csv").exists()
    assert len(summary) == 4
    assert set(summary["change_type"]) == {
        ChangeType.ADDED.value,
        ChangeType.DELETED.value,
        ChangeType.MODIFIED.value,
        ChangeType.UNCHANGED.value,
    }


def test_export_overall_summary_has_one_row_per_compare_file(tmp_path: Path):
    results = _make_results_gdf()
    summary = export_summary_csv(results, tmp_path)

    export_overall_summary({"compare_a": summary, "compare_b": summary}, tmp_path)

    with open(tmp_path / "overall_summary.csv") as f:
        lines = f.read().strip().splitlines()
    assert len(lines) == 3
