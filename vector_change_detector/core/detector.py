from __future__ import annotations

import uuid
from enum import Enum

import geopandas as gpd

from vector_change_detector.core.matcher import Match


class ChangeType(str, Enum):
    """The classification assigned to each matched or unmatched polygon."""

    ADDED = "Added"
    DELETED = "Deleted"
    MODIFIED = "Modified"
    UNCHANGED = "Unchanged"


def classify_match(match: Match, unchanged_iou_threshold: float) -> ChangeType:
    """Classify a single Match into a ChangeType.

    Args:
        match: The spatial match to classify.
        unchanged_iou_threshold: IoU at or above which a matched pair is
            considered Unchanged rather than Modified.

    Returns:
        Added if the polygon exists only in the comparison dataset,
        Deleted if it exists only in the reference dataset, Unchanged if
        both exist and their IoU meets the threshold, otherwise Modified.
    """
    if match.ref_index is None:
        return ChangeType.ADDED
    if match.compare_index is None:
        return ChangeType.DELETED
    if match.iou >= unchanged_iou_threshold:
        return ChangeType.UNCHANGED
    return ChangeType.MODIFIED


def detect_changes(
    reference_gdf: gpd.GeoDataFrame,
    compare_gdf: gpd.GeoDataFrame,
    matches: list[Match],
    unchanged_iou_threshold: float = 0.90,
) -> gpd.GeoDataFrame:
    """Build the full change-detection result set from a list of matches.

    Args:
        reference_gdf: Cleaned reference GeoDataFrame.
        compare_gdf: Cleaned comparison GeoDataFrame.
        matches: Output of matcher.match_datasets for this pair.
        unchanged_iou_threshold: IoU at or above which a matched pair is
            considered Unchanged rather than Modified.

    Returns:
        A GeoDataFrame with one row per match, carrying change_id,
        change_type, old_area, new_area, area_diff, pct_change, overlap_pct,
        iou, centroid_distance, reference_index, compare_index, and geometry
        (the comparison geometry for Added/Modified/Unchanged, the reference
        geometry for Deleted).
    """
    records = []

    for match in matches:
        change_type = classify_match(match, unchanged_iou_threshold)

        if change_type == ChangeType.ADDED:
            geom = compare_gdf.geometry.loc[match.compare_index]
            old_area = 0.0
            new_area = geom.area
        elif change_type == ChangeType.DELETED:
            geom = reference_gdf.geometry.loc[match.ref_index]
            old_area = geom.area
            new_area = 0.0
        else:
            ref_geom = reference_gdf.geometry.loc[match.ref_index]
            new_geom = compare_gdf.geometry.loc[match.compare_index]
            geom = new_geom
            old_area = ref_geom.area
            new_area = new_geom.area

        area_diff = new_area - old_area
        pct_change = (area_diff / old_area * 100.0) if old_area > 0 else None

        records.append(
            {
                "change_id": str(uuid.uuid4()),
                "change_type": change_type.value,
                "old_area": old_area,
                "new_area": new_area,
                "area_diff": area_diff,
                "pct_change": pct_change,
                "overlap_pct": match.overlap_ref_pct,
                "iou": match.iou,
                "centroid_distance": match.centroid_distance,
                "reference_index": match.ref_index,
                "compare_index": match.compare_index,
                "geometry": geom,
            }
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs=reference_gdf.crs)
