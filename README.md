# Vector Change Detector

A CLI tool that spatially compares a **reference** vector dataset (GeoJSON or
Shapefile) against one or more **comparison** datasets and reports Added,
Deleted, Modified, and Unchanged polygons. Matching is purely spatial
(overlap / IoU) — feature IDs and attributes are never used, so it works even
when the two datasets use unrelated ID schemes.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m vector_change_detector.main \
  --reference sample_data/reference.geojson \
  --compare sample_data/compare_a.geojson sample_data/compare_b.geojson \
  --output output \
  --threshold 0.90
```

Run from the repository root, with `--compare` accepting any number of
comparison datasets. Each is compared independently against the same
reference dataset.

## Output

```
output/
  compare_a/
    Added.geojson       # polygons only in compare_a
    Deleted.geojson     # polygons only in reference
    Modified.geojson    # matched polygons whose shape/area changed
    Changes.geojson      # Added + Deleted + Modified combined
    Summary.csv          # counts and area totals per change type
  compare_b/
    ...
  overall_summary.csv    # one row per comparison file, all counts/areas
```

Unchanged polygons are computed internally (for the Summary.csv counts) but
are not written to their own GeoJSON layer.

## How matching works

1. Both the reference and each comparison dataset are cleaned: invalid
   geometries are repaired, empty/null/non-polygonal rows are dropped, the
   comparison dataset is reprojected to the reference's CRS if needed, and
   optional sliver polygons below `--min-area` are removed.
2. An STRtree spatial index is built over the comparison geometries. For
   every reference polygon, all intersecting comparison polygons are found
   and the one with the highest Intersection-over-Union (IoU) is chosen as
   its match.
3. Each match is classified:
   - No reference counterpart -> **Added**
   - No comparison counterpart -> **Deleted**
   - IoU >= `--threshold` (default 0.90) -> **Unchanged**
   - IoU < `--threshold` -> **Modified**

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--reference` | required | Path to the reference GeoJSON/Shapefile |
| `--compare` | required | One or more comparison GeoJSON/Shapefile paths |
| `--output` | `output` | Output directory |
| `--threshold` | `0.90` | IoU cutoff between Unchanged and Modified |
| `--min-area` | `0.0` | Minimum polygon area to keep; `0` disables sliver filtering |

## Project layout

```
vector_change_detector/
  main.py              CLI entry point
  core/
    loader.py           Load GeoJSON/Shapefile into GeoDataFrames
    geometry_ops.py      Invalid-geometry repair, CRS reprojection, sliver filtering
    matcher.py            STRtree-based spatial matching (IoU, overlap %, centroid distance)
    detector.py            Classification into Added/Deleted/Modified/Unchanged
    exporter.py            GeoJSON + CSV export
    pipeline.py             Orchestrates clean -> match -> classify for one pair
  utils/
    logging_config.py
  tests/                Unit + integration tests
  sample_data/          Small reference/compare fixtures used by the tests
```

Each `core/` module is independent of the CLI and has no I/O side effects
beyond what its name implies, so the same pipeline can later be reused from
a GUI, a QGIS plugin, or a web backend without modification.

## Tests

```bash
pytest
```
