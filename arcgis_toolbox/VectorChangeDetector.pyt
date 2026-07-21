from __future__ import annotations

from pathlib import Path

import arcpy


class Toolbox:
    """ArcGIS Pro Python Toolbox exposing the Vector Change Detector tool."""

    def __init__(self) -> None:
        self.label = "Vector Change Detector"
        self.alias = "vectorchangedetector"
        self.tools = [DetectVectorChanges]


class DetectVectorChanges:
    """Spatially compares a reference dataset against one or more comparison datasets."""

    def __init__(self) -> None:
        self.label = "Detect Vector Changes"
        self.description = (
            "Spatially compares a reference polygon dataset against one or more "
            "comparison datasets using IoU-based matching (feature IDs are never "
            "used). Writes Added/Deleted/Modified/Changes GeoJSON layers and a "
            "Summary.csv per comparison dataset, plus an overall_summary.csv "
            "across all comparisons. Only .shp and .geojson files are supported."
        )
        self.canRunInBackground = False

    def getParameterInfo(self) -> list[arcpy.Parameter]:
        """Declare this tool's input parameters.

        Returns:
            The list of arcpy.Parameter objects shown in the tool's dialog.
        """
        reference = arcpy.Parameter(
            displayName="Reference dataset (.shp or .geojson)",
            name="reference",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        reference.filter.list = ["shp", "geojson", "json"]

        compare = arcpy.Parameter(
            displayName="Comparison dataset(s) (.shp or .geojson)",
            name="compare",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        compare.filter.list = ["shp", "geojson", "json"]

        output_folder = arcpy.Parameter(
            displayName="Output folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        threshold = arcpy.Parameter(
            displayName="Unchanged IoU threshold",
            name="threshold",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        threshold.value = 0.90

        min_area = arcpy.Parameter(
            displayName="Minimum polygon area (0 = no filtering)",
            name="min_area",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        min_area.value = 0.0

        return [reference, compare, output_folder, threshold, min_area]

    def isLicensed(self) -> bool:
        """This tool requires no special ArcGIS Pro license."""
        return True

    def updateParameters(self, parameters: list[arcpy.Parameter]) -> None:
        """No dynamic parameter updates are needed for this tool."""
        return

    def updateMessages(self, parameters: list[arcpy.Parameter]) -> None:
        """No custom parameter validation messages are needed for this tool."""
        return

    def execute(self, parameters: list[arcpy.Parameter], messages) -> None:
        """Run the comparison pipeline for every comparison dataset against the reference.

        Args:
            parameters: The tool's resolved parameters, in getParameterInfo order.
            messages: The ArcGIS Pro geoprocessing messages object used for logging.
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
            arcpy.AddError(
                "The 'vector_change_detector' Python package is not installed in "
                "ArcGIS Pro's active Python environment. Clone the default "
                "environment (Settings > Python > Manage Environments > Clone), "
                "activate the clone, then open the 'Python Command Prompt' from "
                "the Start menu and run: pip install vector-change-detector "
                f"(original error: {exc})"
            )
            raise arcpy.ExecuteError

        reference_path = parameters[0].valueAsText
        compare_paths = [p.strip("'\"") for p in parameters[1].valueAsText.split(";")]
        output_dir = parameters[2].valueAsText
        threshold = float(parameters[3].valueAsText) if parameters[3].valueAsText else 0.90
        min_area = float(parameters[4].valueAsText) if parameters[4].valueAsText else 0.0

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)

        messages.addMessage(f"Loading reference dataset: {reference_path}")
        reference_gdf = load_vector_file(reference_path)

        per_file_summaries = {}
        for compare_path in compare_paths:
            compare_name = Path(compare_path).stem
            messages.addMessage(f"Comparing '{compare_name}' against reference")
            compare_gdf = load_vector_file(compare_path)

            results = run_comparison(
                reference_gdf=reference_gdf,
                compare_gdf=compare_gdf,
                unchanged_iou_threshold=threshold,
                min_area=min_area,
            )

            file_output_dir = output_root / compare_name
            export_category_layers(results, file_output_dir)
            export_changes_layer(results, file_output_dir)
            per_file_summaries[compare_name] = export_summary_csv(results, file_output_dir)

            messages.addMessage(f"Finished '{compare_name}' -> {file_output_dir}")

        export_overall_summary(per_file_summaries, output_root)
        messages.addMessage(f"All comparisons complete. Results written to {output_root}")
