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

Every area figure — `old_area_sqkm`, `new_area_sqkm`, `area_diff_sqkm` in
`Changes.geojson`/`change_type` layers, and `total_old_area_sqkm`,
`total_new_area_sqkm`, `total_area_diff_sqkm` in `Summary.csv` — is in
**square kilometers**, regardless of the input data's original CRS (see "How
matching works" below for why).

## How matching works

1. Both datasets are reprojected into `--area-crs` (default `EPSG:6933`, a
   global equal-area CRS in meters), then cleaned: invalid geometries are
   repaired, empty/null/non-polygonal rows are dropped, exact-duplicate
   geometries within each dataset are dropped (keeping one copy — without
   this, a polygon recorded twice in one file, a common issue in datasets
   merged from multiple sources, would leave its extra copy unmatched and
   misclassified as Added/Deleted even though nothing really changed), and
   sliver polygons below `--min-area` (in square meters) are removed.
   Reprojecting first means area and overlap figures are always real,
   consistent ground measurements — computing area directly on unprojected
   degree coordinates (e.g. plain GeoJSON in EPSG:4326) is not meaningful,
   which is why this step always runs.
2. An STRtree spatial index is built over the comparison geometries. For
   every reference polygon, all intersecting comparison polygons are found
   and the one with the highest Intersection-over-Union (IoU) is chosen as
   its match.
3. Each match is classified:
   - No reference counterpart -> **Added**
   - No comparison counterpart -> **Deleted**
   - IoU >= `--threshold` (default 0.90) -> **Unchanged**
   - IoU < `--threshold` -> **Modified**
4. Areas are converted from the working CRS's square meters to square
   kilometers for every output file.

## Options

| Flag | Default | Meaning |
|---|---|---|
| `--reference` | required | Path to the reference GeoJSON/Shapefile |
| `--compare` | required | One or more comparison GeoJSON/Shapefile paths |
| `--output` | `output` | Output directory |
| `--threshold` | `0.90` | IoU cutoff between Unchanged and Modified |
| `--min-area` | `0.0` | Minimum polygon area in square meters to keep; `0` disables sliver filtering |
| `--area-crs` | `EPSG:6933` | CRS both datasets are reprojected into before matching/area computation |

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
beyond what its name implies, so the same pipeline is reused as-is by the
QGIS and ArcGIS Pro plugins below, with no duplicated logic.

## GIS software plugins

The same tested `core/` pipeline is also available inside QGIS and ArcGIS
Pro, as thin wrappers:

- **QGIS** — a Processing Toolbox algorithm ("Detect Vector Changes"). See
  [`qgis_plugin/README.md`](qgis_plugin/README.md) for install steps.
- **ArcGIS Pro** — a Python Toolbox (`.pyt`) tool. See
  [`arcgis_toolbox/README.md`](arcgis_toolbox/README.md) for install steps.

Both require the `vector-change-detector` package to be installed into that
software's own Python environment first:

```bash
pip install /path/to/mashi
```

(this repo root contains `pyproject.toml`, so `pip install .` from here also
works, and additionally gives you a `vector-change-detector` console command
equivalent to `python -m vector_change_detector.main`)

## Tests

```bash
pytest
```
