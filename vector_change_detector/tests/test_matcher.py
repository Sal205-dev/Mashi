from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Polygon

from vector_change_detector.core.matcher import match_datasets


def _square(x0: float, y0: float, size: float) -> Polygon:
    return Polygon(
        [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size), (x0, y0)]
    )


def test_full_overlap_yields_iou_one():
    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")
    compare = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")

    matches = match_datasets(reference, compare)

    assert len(matches) == 1
    assert matches[0].iou == 1.0
    assert matches[0].ref_index == 0
    assert matches[0].compare_index == 0


def test_partial_overlap_yields_intermediate_iou():
    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")
    compare = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(5, 0, 10)], crs="EPSG:4326")

    matches = match_datasets(reference, compare)

    assert len(matches) == 1
    assert 0.0 < matches[0].iou < 1.0


def test_no_overlap_yields_unmatched_pair():
    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")
    compare = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(100, 100, 10)], crs="EPSG:4326")

    matches = match_datasets(reference, compare)

    assert len(matches) == 2
    ref_only = [m for m in matches if m.ref_index is not None and m.compare_index is None]
    compare_only = [m for m in matches if m.compare_index is not None and m.ref_index is None]
    assert len(ref_only) == 1
    assert len(compare_only) == 1


def test_matching_ignores_feature_ids():
    reference = gpd.GeoDataFrame({"id": [999]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")
    compare = gpd.GeoDataFrame({"id": [1]}, geometry=[_square(0, 0, 10)], crs="EPSG:4326")

    matches = match_datasets(reference, compare)

    assert matches[0].iou == 1.0
