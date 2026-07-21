# Vector Change Detector — QGIS Plugin

Adds a **Detect Vector Changes** algorithm to the Processing Toolbox, under the
**Vector Change Detector** group. It's a thin wrapper around the same
`vector_change_detector` core pipeline used by the CLI — the geometry logic is
identical.

## 1. Install the core package into QGIS's Python environment (one-time)

QGIS ships its own Python; the plugin needs the `vector-change-detector`
package (and its `geopandas`/`shapely`/`pyproj`/`fiona`/`rtree` dependencies)
installed there, not in your regular system Python.

**Windows:**
1. Open **OSGeo4W Shell** from the Start menu (search "OSGeo4W").
2. Run:
   ```
   python -m pip install "C:\path\to\mashi"
   ```
   (point it at the repository root, i.e. the folder containing `pyproject.toml`)

   If that fails with a GDAL/DLL-related error, it usually means pip's
   `fiona`/`geopandas` wheels conflict with QGIS's own bundled GDAL build. In
   that case, use the **OSGeo4W Setup** installer instead (the same one that
   installed QGIS): re-run `osgeo4w-setup.exe`, choose "Advanced Install", and
   search for/install `python3-geopandas` — this installs a version built
   against QGIS's own GDAL, avoiding the conflict.

**macOS / Linux (QGIS installed via its own Python, e.g. from python.org or a
QGIS.app bundle):**
```bash
/path/to/qgis/python3 -m pip install /path/to/mashi
```

## 2. Install the plugin

1. Zip the `qgis_plugin/vector_change_detector` folder itself (so the zip's
   root contains `metadata.txt`, `__init__.py`, etc. directly — not nested
   inside another folder).
   - Windows PowerShell, from the repo root:
     ```powershell
     Compress-Archive -Path qgis_plugin\vector_change_detector -DestinationPath vector_change_detector.zip
     ```
2. In QGIS: **Plugins > Manage and Install Plugins > Install from ZIP**,
   browse to `vector_change_detector.zip`, click **Install Plugin**.
3. If prompted, enable the plugin in the **Installed** tab.

## 3. Run it

Open **Processing Toolbox** (Processing menu, or `Ctrl+Alt+T`), find
**Vector Change Detector > Detect Vector Changes**, double-click it. Fill in:

- **Reference layer** — the baseline dataset (a loaded layer, or browse to a
  `.shp`/`.geojson` file directly)
- **Comparison layer(s)** — one or more datasets to diff against the reference
- **Output folder**
- **Unchanged IoU threshold** (default 0.90)
- **Minimum polygon area** (default 0, no filtering)

Click **Run**. Progress and log messages appear in the algorithm dialog. For
each comparison layer, a subfolder named after it is created under the output
folder containing `Added.geojson`, `Deleted.geojson`, `Modified.geojson`,
`Changes.geojson`, and `Summary.csv`; `overall_summary.csv` sits at the top of
the output folder. Only file-based `.geojson`/`.json`/`.shp` layers are
supported.

## Uninstall / update

**Plugins > Manage and Install Plugins > Installed**, select "Vector Change
Detector", click **Uninstall**. To update after changing the core package,
re-run the `pip install` step in part 1; you only need to reinstall the zip
in part 2 if the plugin files themselves (not the core package) changed.
