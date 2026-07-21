from __future__ import annotations

from pathlib import Path

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
