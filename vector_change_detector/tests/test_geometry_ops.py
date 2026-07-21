from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Polygon

from vector_change_detector.core.geometry_ops import (
    clean_geometries,
    fix_invalid_geometries,
    remove_duplicate_geometries,
    remove_empty_geometries,
    remove_sliver_polygons,
)


def test_fix_invalid_geometries_repairs_bowtie():
    bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[bowtie], crs="EPSG:4326")
    assert not gdf.geometry.iloc[0].is_valid

    fixed = fix_invalid_geometries(gdf)
    assert fixed.geometry.iloc[0].is_valid


def test_remove_empty_geometries_drops_none_and_empty():
    valid = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[valid, Polygon(), None],
        crs="EPSG:4326",
    )

    result = remove_empty_geometries(gdf)

    assert len(result) == 1


def test_remove_sliver_polygons_filters_by_min_area():
    small = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    large = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[small, large], crs="EPSG:4326")

    result = remove_sliver_polygons(gdf, min_area=5.0)

    assert len(result) == 1
    assert result.iloc[0]["id"] == 2


def test_remove_sliver_polygons_disabled_when_min_area_zero():
    small = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[small], crs="EPSG:4326")

    result = remove_sliver_polygons(gdf, min_area=0.0)

    assert len(result) == 1


def test_remove_duplicate_geometries_keeps_first_occurrence():
    a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    duplicate_of_a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    b = Polygon([(5, 5), (6, 5), (6, 6), (5, 6), (5, 5)])
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[a, duplicate_of_a, b],
        crs="EPSG:4326",
    )

    result = remove_duplicate_geometries(gdf)

    assert len(result) == 2
    assert list(result["id"]) == [1, 3]


def test_clean_geometries_reprojects_to_target_crs():
    valid = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[valid], crs="EPSG:4326")

    cleaned = clean_geometries(gdf, target_crs="EPSG:3857")

    assert cleaned.crs.to_string() == "EPSG:3857"


def test_clean_geometries_drops_non_polygonal_rows():
    from shapely.geometry import LineString

    valid = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    line = LineString([(0, 0), (1, 1)])
    gdf = gpd.GeoDataFrame({"id": [1, 2]}, geometry=[valid, line], crs="EPSG:4326")

    cleaned = clean_geometries(gdf)

    assert len(cleaned) == 1
    assert cleaned.iloc[0]["id"] == 1
