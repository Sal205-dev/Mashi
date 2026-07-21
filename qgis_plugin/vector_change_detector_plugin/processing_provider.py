from __future__ import annotations

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .vector_change_algorithm import DetectVectorChangesAlgorithm


class VectorChangeDetectorProvider(QgsProcessingProvider):
    """Processing provider exposing the Vector Change Detector algorithm(s)."""

    def id(self) -> str:
        """Return the unique provider ID used internally by Processing."""
        return "vectorchangedetector"

    def name(self) -> str:
        """Return the provider's display name shown in the Processing Toolbox."""
        return "Vector Change Detector"

    def icon(self) -> QIcon:
        """Return the provider icon; a blank icon falls back to Processing's default."""
        return QIcon()

    def loadAlgorithms(self) -> None:
        """Register every algorithm this provider exposes."""
        self.addAlgorithm(DetectVectorChangesAlgorithm())
