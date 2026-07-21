from __future__ import annotations

import geopandas as gpd

from vector_change_detector.core.detector import detect_changes
from vector_change_detector.core.geometry_ops import clean_geometries
from vector_change_detector.core.matcher import match_datasets


def run_comparison(
    reference_gdf: gpd.GeoDataFrame,
    compare_gdf: gpd.GeoDataFrame,
    unchanged_iou_threshold: float = 0.90,
    min_area: float = 0.0,
) -> gpd.GeoDataFrame:
    """Run the full clean -> match -> classify pipeline for one dataset pair.

    Args:
        reference_gdf: Raw reference GeoDataFrame.
        compare_gdf: Raw comparison GeoDataFrame. Reprojected to the
            reference's CRS if they differ.
        unchanged_iou_threshold: IoU at or above which a matched pair is
            considered Unchanged rather than Modified.
        min_area: Minimum polygon area to retain in both datasets; smaller
            slivers are dropped before matching. 0 disables filtering.

    Returns:
        The full change-detection result set, as returned by
        detector.detect_changes.
    """
    reference_clean = clean_geometries(reference_gdf, min_area=min_area)
    compare_clean = clean_geometries(compare_gdf, target_crs=reference_clean.crs, min_area=min_area)
    matches = match_datasets(reference_clean, compare_clean)
    return detect_changes(reference_clean, compare_clean, matches, unchanged_iou_threshold)
