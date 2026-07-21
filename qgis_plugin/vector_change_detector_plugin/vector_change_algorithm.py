from __future__ import annotations

from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
)

SUPPORTED_SUFFIXES = {".geojson", ".json", ".shp"}
DEFAULT_AREA_CRS = "EPSG:6933"


class DetectVectorChangesAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm wrapping vector_change_detector's core comparison pipeline.

    Spatially compares a reference polygon layer against one or more comparison
    polygon layers and writes Added/Deleted/Modified/Changes GeoJSON layers plus
    Summary.csv per comparison, and an overall_summary.csv across all of them.
    """

    REFERENCE = "REFERENCE"
    COMPARE = "COMPARE"
    OUTPUT = "OUTPUT"
    THRESHOLD = "THRESHOLD"
    MIN_AREA = "MIN_AREA"
    AREA_CRS = "AREA_CRS"

    def createInstance(self) -> "DetectVectorChangesAlgorithm":
        """Return a new, unconfigured instance of this algorithm."""
        return DetectVectorChangesAlgorithm()

    def name(self) -> str:
        """Return the algorithm's unique internal ID."""
        return "detect_vector_changes"

    def displayName(self) -> str:
        """Return the algorithm's display name shown in the Processing Toolbox."""
        return "Detect Vector Changes"

    def group(self) -> str:
        """Return the display name of the group this algorithm belongs to."""
        return "Vector Change Detector"

    def groupId(self) -> str:
        """Return the internal ID of the group this algorithm belongs to."""
        return "vectorchangedetector"

    def shortHelpString(self) -> str:
        """Return the help text shown in the algorithm dialog."""
        return (
            "Spatially compares a reference polygon layer against one or more "
            "comparison polygon layers using IoU-based matching (feature IDs are "
            "never used). For each comparison layer, writes Added.geojson, "
            "Deleted.geojson, Modified.geojson, Changes.geojson, and Summary.csv "
            "into a subfolder of the output folder (named after that layer), plus "
            "an overall_summary.csv across all comparisons. Areas are reported in "
            "square kilometers, after both datasets are reprojected into the "
            "Area CRS parameter (a global equal-area CRS by default) so figures "
            "are meaningful regardless of the input data's original CRS.\n\n"
            "Only file-based GeoJSON (.geojson/.json) and Shapefile (.shp) layers "
            "are supported.\n\n"
            "Requires the 'vector_change_detector' Python package (and its "
            "geopandas/shapely/pyproj/fiona/rtree dependencies) to be installed in "
            "QGIS's Python environment."
        )

    def initAlgorithm(self, config=None) -> None:
        """Declare this algorithm's input and output parameters."""
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.REFERENCE,
                "Reference layer",
                types=[QgsProcessing.TypeVectorPolygon],
            )
        )
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.COMPARE,
                "Comparison layer(s)",
                layerType=QgsProcessing.TypeVectorPolygon,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT,
                "Output folder",
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.THRESHOLD,
                "Unchanged IoU threshold",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.90,
                minValue=0.0,
                maxValue=1.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_AREA,
                "Minimum polygon area in square meters (0 = no filtering)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.AREA_CRS,
                "Area CRS (both layers are reprojected here before comparison)",
                defaultValue=QgsCoordinateReferenceSystem(DEFAULT_AREA_CRS),
            )
        )

    @staticmethod
    def _layer_source_path(layer) -> str:
        """Resolve a QGIS layer to the on-disk file path this tool can read.

        Args:
            layer: A QgsVectorLayer whose source is a GeoJSON or Shapefile.

        Returns:
            The filesystem path to the layer's source file.

        Raises:
            QgsProcessingException: If the layer's source is not a supported
                file-based GeoJSON or Shapefile.
        """
        path = layer.source().split("|")[0]
        if Path(path).suffix.lower() not in SUPPORTED_SUFFIXES:
            raise QgsProcessingException(
                f"Unsupported layer source '{path}'. This tool only supports "
                "file-based GeoJSON (.geojson/.json) or Shapefile (.shp) layers."
            )
        return path

    def processAlgorithm(self, parameters, context, feedback):
        """Run the comparison pipeline for every comparison layer against the reference.

        Args:
            parameters: The algorithm's resolved parameter values.
            context: The QgsProcessingContext for this run.
            feedback: The QgsProcessingFeedback used for progress/log/cancellation.

        Returns:
            A dict mapping the OUTPUT parameter name to the output folder path.
        """
        try:
            from vector_change_detector.core.exporter import (
                export_category_layers,
                export_changes_layer,
                export_overall_summary,
                export_summary_csv,
            )
            from vector_change_detector.core.loader import load_vector_file
            from vector_change_detector.core.pipeline import run_comparison
        except ImportError as exc:
            raise QgsProcessingException(
                "The 'vector_change_detector' Python package is not installed in "
                "QGIS's Python environment. Open the OSGeo4W Shell (Windows) or a "
                "terminal where QGIS's Python is on PATH and run: "
                "pip install vector-change-detector "
                f"(original error: {exc})"
            )

        reference_layer = self.parameterAsVectorLayer(parameters, self.REFERENCE, context)
        compare_layers = self.parameterAsLayerList(parameters, self.COMPARE, context)
        output_dir = self.parameterAsString(parameters, self.OUTPUT, context)
        threshold = self.parameterAsDouble(parameters, self.THRESHOLD, context)
        min_area = self.parameterAsDouble(parameters, self.MIN_AREA, context)
        area_crs = self.parameterAsCrs(parameters, self.AREA_CRS, context).authid()

        if not compare_layers:
            raise QgsProcessingException("At least one comparison layer is required.")

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        reference_path = self._layer_source_path(reference_layer)
        feedback.pushInfo(f"Loading reference dataset: {reference_path}")
        reference_gdf = load_vector_file(reference_path)

        per_file_summaries = {}
        total = len(compare_layers)
        for i, compare_layer in enumerate(compare_layers):
            if feedback.isCanceled():
                break

            compare_path = self._layer_source_path(compare_layer)
            compare_name = Path(compare_path).stem
            feedback.pushInfo(f"Comparing '{compare_name}' against reference")
            compare_gdf = load_vector_file(compare_path)

            results = run_comparison(
                reference_gdf=reference_gdf,
                compare_gdf=compare_gdf,
                unchanged_iou_threshold=threshold,
                min_area=min_area,
                area_crs=area_crs,
            )

            file_output_dir = output_root / compare_name
            export_category_layers(results, file_output_dir)
            export_changes_layer(results, file_output_dir)
            per_file_summaries[compare_name] = export_summary_csv(results, file_output_dir)

            feedback.pushInfo(f"Finished '{compare_name}' -> {file_output_dir}")
            feedback.setProgress(int((i + 1) / total * 100))

        export_overall_summary(per_file_summaries, output_root)
        feedback.pushInfo(f"All comparisons complete. Results written to {output_root}")

        return {self.OUTPUT: str(output_root)}
