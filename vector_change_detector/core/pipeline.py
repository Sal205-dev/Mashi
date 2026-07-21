from __future__ import annotations

import geopandas as gpd

from vector_change_detector.core.detector import detect_changes
from vector_change_detector.core.geometry_ops import clean_geometries
from vector_change_detector.core.matcher import match_datasets

DEFAULT_AREA_CRS = "EPSG:6933"
SQUARE_METERS_PER_SQUARE_KM = 1_000_000.0

AREA_COLUMN_RENAMES = {
    "old_area": "old_area_sqkm",
    "new_area": "new_area_sqkm",
    "area_diff": "area_diff_sqkm",
}


def run_comparison(
    reference_gdf: gpd.GeoDataFrame,
    compare_gdf: gpd.GeoDataFrame,
    unchanged_iou_threshold: float = 0.90,
    min_area: float = 0.0,
    area_crs: str = DEFAULT_AREA_CRS,
) -> gpd.GeoDataFrame:
    """Run the full clean -> match -> classify pipeline for one dataset pair.

    Both datasets are reprojected to area_crs (a meter-based equal-area CRS by
    default) before matching, so area and min_area are always measured in real,
    consistent ground units rather than degrees or an arbitrary input CRS.

    Args:
        reference_gdf: Raw reference GeoDataFrame.
        compare_gdf: Raw comparison GeoDataFrame.
        unchanged_iou_threshold: IoU at or above which a matched pair is
            considered Unchanged rather than Modified.
        min_area: Minimum polygon area, in square meters (the units of
            area_crs), to retain in both datasets; smaller slivers are
            dropped before matching. 0 disables filtering.
        area_crs: CRS to reproject both datasets into before matching and
            computing area. Defaults to EPSG:6933, a global equal-area CRS in
            meters, so area figures are meaningful regardless of the input
            data's original CRS.

    Returns:
        The full change-detection result set, as returned by
        detector.detect_changes, with old_area_sqkm, new_area_sqkm, and
        area_diff_sqkm columns (in square kilometers) in place of
        detect_changes' raw old_area/new_area/area_diff.
    """
    reference_clean = clean_geometries(reference_gdf, target_crs=area_crs, min_area=min_area)
    compare_clean = clean_geometries(compare_gdf, target_crs=area_crs, min_area=min_area)
    matches = match_datasets(reference_clean, compare_clean)
    results = detect_changes(reference_clean, compare_clean, matches, unchanged_iou_threshold)

    for column in AREA_COLUMN_RENAMES:
        results[column] = results[column] / SQUARE_METERS_PER_SQUARE_KM
    return results.rename(columns=AREA_COLUMN_RENAMES)
