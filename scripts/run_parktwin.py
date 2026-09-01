import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from detection.yolo_detector import VehicleDetector  # noqa: E402
from parktwin.pipeline import process_parking_image  # noqa: E402
from twin.repository import TwinRepository  # noqa: E402


def main() -> None:
    logging.basicConfig(level=os.getenv("PARKTWIN_LOG_LEVEL", "INFO"))
    parser = argparse.ArgumentParser(description="Run the full ParkTwin pipeline.")
    parser.add_argument("image_path", help="Path to the input image.")
    parser.add_argument(
        "--spots",
        default=os.getenv(
            "PARKTWIN_SPOTS_PATH", PROJECT_ROOT / "data" / "samples" / "spots_annotated.json"
        ),
        help="Path to the parking spots JSON file.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("PARKTWIN_MODEL_PATH", "yolo11s.pt"),
        help="Path to the YOLO model file. Default: yolo11s.pt",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=int(os.getenv("PARKTWIN_IMGSZ", "1280")),
        help="YOLO inference image size. Default: 1280",
    )
    parser.add_argument(
        "--occupancy-threshold",
        type=float,
        default=float(os.getenv("PARKTWIN_OCCUPANCY_THRESHOLD", "0.1")),
        help="Minimum bbox area ratio inside a spot to mark it occupied. Default: 0.1",
    )
    parser.add_argument(
        "--uncertain-overlap-threshold",
        type=float,
        default=float(os.getenv("PARKTWIN_UNCERTAIN_OVERLAP_THRESHOLD", "0.05")),
        help="Minimum overlap ratio to mark a spot uncertain. Default: 0.05.",
    )
    parser.add_argument(
        "--change-confirmation-frames",
        type=int,
        default=int(os.getenv("PARKTWIN_CHANGE_CONFIRMATION_FRAMES", "2")),
        help="Consecutive frames required to confirm a status change. Default: 2.",
    )
    parser.add_argument(
        "--retention-snapshots",
        type=int,
        default=int(os.getenv("PARKTWIN_RETENTION_SNAPSHOTS", "10000")),
        help="Maximum snapshots retained per parking lot. Default: 10000.",
    )
    parser.add_argument(
        "--parking-lot-id",
        default=os.getenv("PARKTWIN_PARKING_LOT_ID", "default"),
        help="Parking lot identifier stored in the twin state.",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("PARKTWIN_DB_PATH", PROJECT_ROOT / "data" / "parktwin.db"),
        help="SQLite database path. Default: data/parktwin.db",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("PARKTWIN_OUTPUTS_DIR", PROJECT_ROOT / "data" / "outputs"),
        help="Directory where latest_annotated.jpg will be saved.",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_image_path = output_dir / "latest_annotated.jpg"

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    repository = TwinRepository(args.db)
    result = process_parking_image(
        image_path=image_path,
        spots_path=args.spots,
        detector=detector,
        repository=repository,
        parking_lot_id=args.parking_lot_id,
        annotated_image_path=output_image_path,
        occupancy_threshold=args.occupancy_threshold,
        uncertain_overlap_threshold=args.uncertain_overlap_threshold,
        change_confirmation_frames=args.change_confirmation_frames,
        retention_snapshots=args.retention_snapshots,
    )
    state = result.state

    print(f"Snapshot saved to SQLite: {Path(args.db)}")
    print(f"Annotated image saved to: {output_image_path}")
    print(f"Occupancy: {state.occupied_count}/{state.total_spots} ({state.occupancy_rate:.1%})")


if __name__ == "__main__":
    main()
