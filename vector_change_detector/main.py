from __future__ import annotations

import argparse
import logging
from pathlib import Path

from vector_change_detector.core.exporter import (
    export_category_layers,
    export_changes_layer,
    export_overall_summary,
    export_summary_csv,
)
from vector_change_detector.core.loader import load_vector_file
from vector_change_detector.core.pipeline import run_comparison
from vector_change_detector.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the change-detection CLI.

    Returns:
        The parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Detect spatial changes between a reference vector dataset and one "
            "or more comparison datasets (GeoJSON or Shapefile)."
        )
    )
    parser.add_argument(
        "--reference",
        required=True,
        help="Path to the reference dataset (GeoJSON or Shapefile).",
    )
    parser.add_argument(
        "--compare",
        required=True,
        nargs="+",
        help="Paths to one or more comparison datasets, each compared against --reference.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory (default: output).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help=(
            "IoU threshold at or above which a matched polygon is considered "
            "Unchanged rather than Modified (default: 0.90)."
        ),
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=0.0,
        help=(
            "Minimum polygon area to keep, in CRS units; smaller sliver "
            "polygons are dropped before comparison (default: 0, no filtering)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run the reference-vs-comparisons change-detection CLI end to end."""
    configure_logging()
    args = parse_args()

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    logger.info("Loading reference dataset: %s", args.reference)
    reference_gdf = load_vector_file(args.reference)

    per_file_summaries = {}
    for compare_path in args.compare:
        compare_name = Path(compare_path).stem
        logger.info("Comparing '%s' against reference", compare_name)
        compare_gdf = load_vector_file(compare_path)

        results = run_comparison(
            reference_gdf=reference_gdf,
            compare_gdf=compare_gdf,
            unchanged_iou_threshold=args.threshold,
            min_area=args.min_area,
        )

        file_output_dir = output_root / compare_name
        export_category_layers(results, file_output_dir)
        export_changes_layer(results, file_output_dir)
        per_file_summaries[compare_name] = export_summary_csv(results, file_output_dir)

        logger.info("Finished comparison for '%s' -> %s", compare_name, file_output_dir)

    export_overall_summary(per_file_summaries, output_root)
    logger.info("All comparisons complete. Results written to %s", output_root)


if __name__ == "__main__":
    main()
