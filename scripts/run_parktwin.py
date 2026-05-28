import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from detection.yolo_detector import VehicleDetector  # noqa: E402
from parking.loader import load_parking_spots  # noqa: E402
from parking.occupancy import assign_occupancy  # noqa: E402
from parking.visualizer import save_annotated_image  # noqa: E402
from twin.repository import TwinRepository  # noqa: E402
from twin.state_manager import update_twin_state  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full ParkTwin pipeline.")
    parser.add_argument("image_path", help="Path to the input image.")
    parser.add_argument(
        "--spots",
        default=PROJECT_ROOT / "data" / "samples" / "spots_annotated.json",
        help="Path to the parking spots JSON file.",
    )
    parser.add_argument(
        "--model",
        default="yolo11s.pt",
        help="Path to the YOLO model file. Default: yolo11s.pt",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=1280,
        help="YOLO inference image size. Default: 1280",
    )
    parser.add_argument(
        "--occupancy-threshold",
        type=float,
        default=0.1,
        help="Minimum bbox area ratio inside a spot to mark it occupied. Default: 0.1",
    )
    parser.add_argument(
        "--parking-lot-id",
        default="default",
        help="Parking lot identifier stored in the twin state.",
    )
    parser.add_argument(
        "--db",
        default=PROJECT_ROOT / "data" / "parktwin.db",
        help="SQLite database path. Default: data/parktwin.db",
    )
    parser.add_argument(
        "--output-dir",
        default=PROJECT_ROOT / "data" / "outputs",
        help="Directory where latest_annotated.jpg will be saved.",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_dir = Path(args.output_dir)
    output_image_path = output_dir / "latest_annotated.jpg"

    spots = load_parking_spots(args.spots)
    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    detections = detector.detect(image_path)
    occupied_spots = assign_occupancy(
        spots,
        detections,
        overlap_threshold=args.occupancy_threshold,
    )

    repository = TwinRepository(args.db)
    previous_state = repository.get_latest_snapshot()
    state = update_twin_state(
        parking_lot_id=args.parking_lot_id,
        current_spot_statuses=occupied_spots,
        previous_state=previous_state,
    )

    repository.save_snapshot(state)
    repository.save_spot_events(state)
    save_annotated_image(image_path, occupied_spots, detections, output_image_path)

    print(f"Snapshot saved to SQLite: {Path(args.db)}")
    print(f"Annotated image saved to: {output_image_path}")
    print(
        "Occupancy: "
        f"{state.occupied_count}/{state.total_spots} "
        f"({state.occupancy_rate:.1%})"
    )


if __name__ == "__main__":
    main()
