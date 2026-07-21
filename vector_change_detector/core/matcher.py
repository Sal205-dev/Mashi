from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
from shapely import STRtree


@dataclass(frozen=True)
class Match:
    """One spatial pairing between a reference and a comparison polygon.

    Either ref_index or compare_index may be None (but not both), meaning
    the polygon on the other side has no spatial counterpart: a deletion
    when compare_index is None, an addition when ref_index is None.

    Attributes:
        ref_index: Index label into the reference GeoDataFrame, or None.
        compare_index: Index label into the comparison GeoDataFrame, or None.
        intersection_area: Area of geometric intersection between the pair.
        iou: Intersection-over-Union ratio (0.0 for unmatched pairs).
        overlap_ref_pct: Intersection area as a fraction of the reference
            polygon's area.
        overlap_compare_pct: Intersection area as a fraction of the
            comparison polygon's area.
        centroid_distance: Euclidean distance between the two centroids, in
            CRS units. NaN for unmatched pairs.
    """

    ref_index: int | None
    compare_index: int | None
    intersection_area: float
    iou: float
    overlap_ref_pct: float
    overlap_compare_pct: float
    centroid_distance: float


def match_datasets(reference_gdf: gpd.GeoDataFrame, compare_gdf: gpd.GeoDataFrame) -> list[Match]:
    """Spatially match reference polygons to comparison polygons.

    An STRtree built over the comparison geometries is used to find, for
    every reference polygon, all comparison polygons whose geometry
    intersects it (avoiding an O(n*m) brute-force comparison). Among those
    candidates the one with the highest Intersection-over-Union (IoU) is
    selected as the match. Reference polygons with no intersecting candidate
    become deletions; comparison polygons never selected as a best match
    become additions.

    Matching is purely geometric — feature IDs and attributes are never
    consulted.

    Note: each reference polygon is matched independently and greedily, so a
    single comparison polygon may be selected as the best match for more
    than one reference polygon (e.g. a merge scenario). This is acceptable
    for area/overlap-based change detection but means match assignments are
    not guaranteed to be one-to-one.

    Args:
        reference_gdf: Cleaned reference GeoDataFrame.
        compare_gdf: Cleaned comparison GeoDataFrame, in the same CRS as
            reference_gdf.

    Returns:
        A list of Match records covering every reference polygon (matched or
        deleted) and every comparison polygon that was not selected as any
        reference polygon's best match (additions).
    """
    compare_geoms = compare_gdf.geometry.to_numpy()
    tree = STRtree(compare_geoms)

    matched_compare_indices: set = set()
    matches: list[Match] = []

    for ref_idx, ref_geom in zip(reference_gdf.index, reference_gdf.geometry):
        candidate_positions = tree.query(ref_geom, predicate="intersects")
        if len(candidate_positions) == 0:
            matches.append(Match(ref_idx, None, 0.0, 0.0, 0.0, 0.0, float("nan")))
            continue

        best: Match | None = None
        for pos in candidate_positions:
            compare_idx = compare_gdf.index[pos]
            compare_geom = compare_geoms[pos]

            intersection_area = ref_geom.intersection(compare_geom).area
            union_area = ref_geom.union(compare_geom).area
            iou = intersection_area / union_area if union_area > 0 else 0.0

            if best is None or iou > best.iou:
                overlap_ref_pct = intersection_area / ref_geom.area if ref_geom.area > 0 else 0.0
                overlap_compare_pct = (
                    intersection_area / compare_geom.area if compare_geom.area > 0 else 0.0
                )
                centroid_distance = ref_geom.centroid.distance(compare_geom.centroid)
                best = Match(
                    ref_idx,
                    compare_idx,
                    intersection_area,
                    iou,
                    overlap_ref_pct,
                    overlap_compare_pct,
                    centroid_distance,
                )

        matches.append(best)
        matched_compare_indices.add(best.compare_index)

    for compare_idx in compare_gdf.index:
        if compare_idx not in matched_compare_indices:
            matches.append(Match(None, compare_idx, 0.0, 0.0, 0.0, 0.0, float("nan")))

    return matches
