from __future__ import annotations

from qgis.core import QgsApplication

from .processing_provider import VectorChangeDetectorProvider


class VectorChangeDetectorPlugin:
    """QGIS plugin wrapper that registers the Vector Change Detector Processing provider."""

    def __init__(self, iface) -> None:
        """Store the QGIS interface handle.

        Args:
            iface: The active QgisInterface instance, provided by QGIS.
        """
        self.iface = iface
        self.provider: VectorChangeDetectorProvider | None = None

    def initGui(self) -> None:
        """Register the Processing provider when the plugin is loaded."""
        self.provider = VectorChangeDetectorProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self) -> None:
        """Unregister the Processing provider when the plugin is unloaded."""
        QgsApplication.processingRegistry().removeProvider(self.provider)
