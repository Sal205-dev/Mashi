from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from vector_change_detector.core.exporter import (
    export_category_layers,
    export_changes_layer,
    export_summary_csv,
)
from vector_change_detector.core.loader import load_vector_file
from vector_change_detector.core.pipeline import run_comparison

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def test_full_pipeline_on_sample_data_compare_a(tmp_path: Path):
    reference = load_vector_file(SAMPLE_DIR / "reference.geojson")
    compare_a = load_vector_file(SAMPLE_DIR / "compare_a.geojson")

    results = run_comparison(reference, compare_a, unchanged_iou_threshold=0.90, min_area=0.0)

    export_category_layers(results, tmp_path)
    export_changes_layer(results, tmp_path)
    summary = export_summary_csv(results, tmp_path)

    assert (tmp_path / "Added.geojson").exists()
    assert (tmp_path / "Deleted.geojson").exists()
    assert (tmp_path / "Modified.geojson").exists()
    assert (tmp_path / "Changes.geojson").exists()
    assert (tmp_path / "Summary.csv").exists()

    counts = dict(zip(summary["change_type"], summary["count"]))
    assert counts["Added"] == 1
    assert counts["Deleted"] == 1
    assert counts["Modified"] == 2
    assert counts["Unchanged"] == 1


def test_full_pipeline_on_sample_data_compare_b(tmp_path: Path):
    reference = load_vector_file(SAMPLE_DIR / "reference.geojson")
    compare_b = load_vector_file(SAMPLE_DIR / "compare_b.geojson")

    results = run_comparison(reference, compare_b, unchanged_iou_threshold=0.90, min_area=0.0)
    summary = export_summary_csv(results, tmp_path)

    counts = dict(zip(summary["change_type"], summary["count"]))
    assert counts["Added"] == 1
    assert counts["Deleted"] == 1
    assert counts["Modified"] == 0
    assert counts["Unchanged"] == 3


def test_run_comparison_does_not_misclassify_a_duplicated_unchanged_feature_as_added(tmp_path: Path):
    unchanged = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[unchanged], crs="EPSG:3857")
    # The comparison dataset contains an exact duplicate of the one unchanged
    # feature -- a common real-world data quality issue (e.g. a polygon
    # recorded twice after merging multiple source files). Without
    # deduplication, only one copy can be matched, and the extra copy is
    # misclassified as Added even though nothing actually changed.
    compare = gpd.GeoDataFrame(
        {"id": [101, 102]},
        geometry=[unchanged, unchanged],
        crs="EPSG:3857",
    )

    results = run_comparison(reference, compare, unchanged_iou_threshold=0.90, area_crs="EPSG:3857")
    summary = export_summary_csv(results, tmp_path)

    counts = dict(zip(summary["change_type"], summary["count"]))
    assert counts["Added"] == 0
    assert counts["Unchanged"] == 1
