from __future__ import annotations


def classFactory(iface):
    """QGIS plugin entry point, called by the QGIS plugin loader.

    Args:
        iface: The active QgisInterface instance, provided by QGIS.

    Returns:
        An instance of VectorChangeDetectorPlugin.
    """
    from .plugin import VectorChangeDetectorPlugin

    return VectorChangeDetectorPlugin(iface)
