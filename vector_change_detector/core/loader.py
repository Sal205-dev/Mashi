from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".geojson", ".json", ".shp"}


@dataclass
class Dataset:
    """A named vector dataset loaded from disk.

    Attributes:
        name: Human-readable identifier, derived from the filename unless
            explicitly overridden.
        path: Filesystem path the dataset was loaded from.
        gdf: The loaded GeoDataFrame.
    """

    name: str
    path: Path
    gdf: gpd.GeoDataFrame


def load_vector_file(path: str | Path) -> gpd.GeoDataFrame:
    """Load a GeoJSON or Shapefile into a GeoDataFrame.

    Args:
        path: Path to a .geojson, .json, or .shp file.

    Returns:
        The loaded GeoDataFrame, unmodified.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is unsupported, the dataset is
            empty, or the dataset has no CRS defined.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type '{path.suffix}' for {path}. "
            f"Supported types: {sorted(SUPPORTED_SUFFIXES)}"
        )

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError(f"Dataset is empty: {path}")
    if gdf.crs is None:
        raise ValueError(
            f"Dataset has no CRS defined: {path}. Assign a CRS before running comparison."
        )

    logger.info("Loaded %d features from %s (CRS=%s)", len(gdf), path, gdf.crs)
    return gdf


def load_dataset(path: str | Path, name: str | None = None) -> Dataset:
    """Load a vector file into a named Dataset.

    Args:
        path: Path to a .geojson, .json, or .shp file.
        name: Optional display name; defaults to the file's stem.

    Returns:
        A Dataset wrapping the loaded GeoDataFrame.
    """
    path = Path(path)
    gdf = load_vector_file(path)
    return Dataset(name=name or path.stem, path=path, gdf=gdf)
