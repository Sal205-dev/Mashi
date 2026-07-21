from __future__ import annotations

import logging

import geopandas as gpd
from shapely import make_valid

logger = logging.getLogger(__name__)


def fix_invalid_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repair invalid geometries (e.g. self-intersecting polygons) in place.

    Args:
        gdf: Input GeoDataFrame.

    Returns:
        A copy of gdf with invalid geometries replaced by their repaired
        equivalents. Valid geometries are left untouched.
    """
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        logger.info("Repairing %d invalid geometries", int(invalid_mask.sum()))
        gdf = gdf.copy()
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].apply(make_valid)
    return gdf


def remove_empty_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop rows with null or empty geometries.

    Args:
        gdf: Input GeoDataFrame.

    Returns:
        A GeoDataFrame with null/empty geometries removed and the index reset.
    """
    non_empty_mask = ~(gdf.geometry.isna() | gdf.geometry.is_empty)
    dropped = int((~non_empty_mask).sum())
    if dropped:
        logger.info("Dropping %d empty/null geometries", dropped)
    return gdf.loc[non_empty_mask].reset_index(drop=True)


def keep_polygonal_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only Polygon and MultiPolygon rows, dropping other geometry types.

    Args:
        gdf: Input GeoDataFrame.

    Returns:
        A GeoDataFrame containing only Polygon/MultiPolygon rows, index reset.
    """
    polygonal_mask = gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    dropped = int((~polygonal_mask).sum())
    if dropped:
        logger.warning("Dropping %d non-polygonal geometries", dropped)
    return gdf.loc[polygonal_mask].reset_index(drop=True)


def remove_duplicate_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop rows whose geometry exactly duplicates an earlier row's.

    Real-world administrative/cadastral datasets (especially ones assembled
    from multiple source files) sometimes contain the same polygon more than
    once. Without deduplication, the matcher can only pair one copy with its
    counterpart in the other dataset; any extra copies have nothing left to
    match against and are misclassified as Added or Deleted even though the
    underlying feature is genuinely unchanged.

    Args:
        gdf: Input GeoDataFrame.

    Returns:
        A GeoDataFrame with exact-duplicate geometries removed (the first
        occurrence of each is kept), index reset.
    """
    duplicate_mask = gdf.geometry.duplicated()
    dropped = int(duplicate_mask.sum())
    if dropped:
        logger.warning("Dropping %d duplicate geometries", dropped)
    return gdf.loc[~duplicate_mask].reset_index(drop=True)


def remove_sliver_polygons(gdf: gpd.GeoDataFrame, min_area: float) -> gpd.GeoDataFrame:
    """Drop polygons whose area falls below a minimum threshold.

    Args:
        gdf: Input GeoDataFrame.
        min_area: Minimum area (in the GeoDataFrame's CRS units) required to
            keep a polygon. A value of 0 or less disables filtering.

    Returns:
        A GeoDataFrame with sliver polygons removed, index reset.
    """
    if min_area <= 0:
        return gdf
    mask = gdf.geometry.area >= min_area
    dropped = int((~mask).sum())
    if dropped:
        logger.info("Dropping %d sliver polygons below min area %.6f", dropped, min_area)
    return gdf.loc[mask].reset_index(drop=True)


def reproject_to_crs(gdf: gpd.GeoDataFrame, target_crs) -> gpd.GeoDataFrame:
    """Reproject a GeoDataFrame to a target CRS if it differs from its current one.

    Args:
        gdf: Input GeoDataFrame. Must already have a CRS defined.
        target_crs: The CRS to reproject to (anything accepted by
            GeoDataFrame.to_crs, e.g. an EPSG string or pyproj.CRS).

    Returns:
        The input GeoDataFrame if its CRS already matches target_crs,
        otherwise a reprojected copy.

    Raises:
        ValueError: If gdf has no CRS defined.
    """
    if gdf.crs is None:
        raise ValueError("Dataset has no CRS defined; cannot reproject safely.")
    if gdf.crs != target_crs:
        logger.info("Reprojecting from %s to %s", gdf.crs, target_crs)
        gdf = gdf.to_crs(target_crs)
    return gdf


def clean_geometries(
    gdf: gpd.GeoDataFrame,
    target_crs=None,
    min_area: float = 0.0,
) -> gpd.GeoDataFrame:
    """Run the full geometry-cleaning pipeline on a dataset.

    Applies, in order: keep only polygonal geometries, drop empty/null
    geometries, repair invalid geometries, drop any empty/null results from
    repair, drop exact-duplicate geometries, optionally reproject to a
    common CRS, and drop sliver polygons below min_area.

    Args:
        gdf: Input GeoDataFrame.
        target_crs: Optional CRS to reproject to. If None, no reprojection
            is performed.
        min_area: Minimum polygon area to retain; 0 disables sliver filtering.

    Returns:
        A cleaned GeoDataFrame with a fresh integer index.
    """
    gdf = keep_polygonal_geometries(gdf)
    gdf = remove_empty_geometries(gdf)
    gdf = fix_invalid_geometries(gdf)
    gdf = keep_polygonal_geometries(gdf)
    gdf = remove_empty_geometries(gdf)
    gdf = remove_duplicate_geometries(gdf)
    if target_crs is not None:
        gdf = reproject_to_crs(gdf, target_crs)
    gdf = remove_sliver_polygons(gdf, min_area)
    return gdf.reset_index(drop=True)
