# Vector Change Detector — ArcGIS Pro Toolbox

`VectorChangeDetector.pyt` is a Python Toolbox exposing a **Detect Vector
Changes** tool. It's a thin wrapper around the same `vector_change_detector`
core pipeline used by the CLI — the geometry logic is identical.

A note on scope: a true native ArcGIS Pro **Add-in** (the kind that shows up
as a ribbon button) requires compiling a `.esriAddinX` with Visual Studio and
the Esri ArcGIS Pro SDK for .NET. A **Python Toolbox** is the standard
lightweight alternative — no compilation, just add the `.pyt` file to the
Catalog and it behaves like any built-in geoprocessing tool, with an
auto-generated parameter form.

## 1. Install the core package into ArcGIS Pro's Python environment (one-time)

ArcGIS Pro's default `arcgispro-py3` conda environment is read-only — you must
clone it first, then install into the clone.

1. In ArcGIS Pro: **Settings (the gear icon) > Python > Manage Environments**.
2. Select `arcgispro-py3`, click **Clone**, give it a name (e.g. `vcd-env`),
   wait for the clone to finish.
3. Select the new cloned environment as **Active**, click **OK**, and restart
   ArcGIS Pro if prompted.
4. Open **Python Command Prompt** from the Start menu (installed alongside
   ArcGIS Pro) — this activates your cloned environment automatically. Run:
   ```
   pip install "C:\path\to\mashi"
   ```
   (point it at the repository root, i.e. the folder containing `pyproject.toml`)

   Alternatively, from the Python Command Prompt you can use conda instead of
   pip for the heavier geospatial dependencies, which avoids most binary
   conflicts:
   ```
   conda install -c conda-forge geopandas shapely pyproj fiona rtree
   pip install "C:\path\to\mashi" --no-deps
   ```

## 2. Add the toolbox

1. In ArcGIS Pro, open the **Catalog** pane.
2. Right-click **Toolboxes > Add Toolbox**.
3. Browse to `arcgis_toolbox\VectorChangeDetector.pyt` and add it.

It now appears in the Catalog as "Vector Change Detector.pyt" containing the
**Detect Vector Changes** tool.

## 3. Run it

Double-click **Detect Vector Changes** to open its parameter form. Fill in:

- **Reference dataset (.shp or .geojson)**
- **Comparison dataset(s) (.shp or .geojson)** — you can select multiple files
- **Output folder**
- **Unchanged IoU threshold** (default 0.90)
- **Minimum polygon area in square meters** (default 0, no filtering)
- **Area CRS** (default `EPSG:6933`, a global equal-area CRS) — both datasets
  are reprojected here before comparison, so area figures are real and
  consistent regardless of the input data's original CRS

Click **Run**. Progress messages appear in the geoprocessing pane. For each
comparison dataset, a subfolder named after it is created under the output
folder containing `Added.geojson`, `Deleted.geojson`, `Modified.geojson`,
`Changes.geojson`, and `Summary.csv`; `overall_summary.csv` sits at the top of
the output folder. All area figures (`old_area_sqkm`, `new_area_sqkm`,
`area_diff_sqkm`, and the `total_*_sqkm` columns in `Summary.csv`) are in
square kilometers.

Only standalone `.shp` and `.geojson`/`.json` files are supported — feature
classes stored inside a File Geodatabase are not (this tool never reads or
writes a geodatabase).

If you already added the toolbox before the Area CRS parameter was added, it
should pick it up automatically the next time you open the tool's parameter
form (ArcGIS Pro re-reads `.pyt` files each time), no need to re-add it.
