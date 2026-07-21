from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

from vector_change_detector.core.detector import ChangeType

logger = logging.getLogger(__name__)

CATEGORY_FILES = {
    ChangeType.ADDED: "Added.geojson",
    ChangeType.DELETED: "Deleted.geojson",
    ChangeType.MODIFIED: "Modified.geojson",
}


def _write_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    """Write a GeoDataFrame to a GeoJSON file, handling the empty case.

    fiona/pyogrio cannot always write a zero-row GeoDataFrame, so an empty
    result is written directly as a valid empty FeatureCollection.

    Args:
        gdf: GeoDataFrame to write (may be empty).
        path: Destination .geojson file path.
    """
    if gdf.empty:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
    else:
        gdf.to_file(path, driver="GeoJSON")
    logger.info("Wrote %d features to %s", len(gdf), path)


def export_category_layers(results_gdf: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Write Added.geojson, Deleted.geojson, and Modified.geojson.

    Args:
        results_gdf: Full change-detection result set from detector.detect_changes.
        output_dir: Directory to write into; created if missing.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for change_type, filename in CATEGORY_FILES.items():
        subset = results_gdf.loc[results_gdf["change_type"] == change_type.value]
        _write_geojson(subset, output_dir / filename)


def export_changes_layer(results_gdf: gpd.GeoDataFrame, output_dir: Path) -> None:
    """Write Changes.geojson containing every Added, Deleted, and Modified polygon.

    Unchanged polygons are excluded.

    Args:
        results_gdf: Full change-detection result set from detector.detect_changes.
        output_dir: Directory to write into; created if missing.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    changed = results_gdf.loc[results_gdf["change_type"] != ChangeType.UNCHANGED.value]
    _write_geojson(changed, output_dir / "Changes.geojson")


def build_summary(results_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Aggregate change counts and areas (in square kilometers) per change type.

    Args:
        results_gdf: Full change-detection result set from pipeline.run_comparison,
            carrying old_area_sqkm, new_area_sqkm, and area_diff_sqkm columns.

    Returns:
        A DataFrame with one row per ChangeType, containing count,
        total_old_area_sqkm, total_new_area_sqkm, and total_area_diff_sqkm.
    """
    rows = []
    for change_type in ChangeType:
        subset = results_gdf.loc[results_gdf["change_type"] == change_type.value]
        rows.append(
            {
                "change_type": change_type.value,
                "count": len(subset),
                "total_old_area_sqkm": subset["old_area_sqkm"].sum(),
                "total_new_area_sqkm": subset["new_area_sqkm"].sum(),
                "total_area_diff_sqkm": subset["area_diff_sqkm"].sum(),
            }
        )
    return pd.DataFrame(rows)


def export_summary_csv(results_gdf: gpd.GeoDataFrame, output_dir: Path) -> pd.DataFrame:
    """Write Summary.csv for a single reference-vs-comparison run.

    Args:
        results_gdf: Full change-detection result set from detector.detect_changes.
        output_dir: Directory to write into; created if missing.

    Returns:
        The summary DataFrame that was written.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results_gdf)
    summary.to_csv(output_dir / "Summary.csv", index=False)
    logger.info("Wrote summary to %s", output_dir / "Summary.csv")
    return summary


def export_overall_summary(per_file_summaries: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """Write overall_summary.csv combining every comparison's Summary.csv into one table.

    Args:
        per_file_summaries: Mapping of comparison dataset name to its
            build_summary output.
        output_dir: Directory to write into; created if missing.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for compare_name, summary in per_file_summaries.items():
        row = {"compare_file": compare_name}
        for _, r in summary.iterrows():
            row[f"{r['change_type']}_count"] = r["count"]
            row[f"{r['change_type']}_area_diff_sqkm"] = r["total_area_diff_sqkm"]
        rows.append(row)

    overall = pd.DataFrame(rows)
    overall.to_csv(output_dir / "overall_summary.csv", index=False)
    logger.info("Wrote overall summary to %s", output_dir / "overall_summary.csv")
