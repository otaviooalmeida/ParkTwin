import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from detection.yolo_detector import VehicleDetector  # noqa: E402
from parking.visualizer import save_annotated_image  # noqa: E402
from parktwin.pipeline import analyze_parking_image  # noqa: E402
from twin.state import build_twin_state, save_twin_state  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ParkTwin pipeline on one image.")
    parser.add_argument("image_path", help="Path to the input image.")
    parser.add_argument(
        "--spots",
        default=PROJECT_ROOT / "data" / "samples" / "spots_sample.json",
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
        "--output-dir",
        default=PROJECT_ROOT / "data" / "outputs",
        help="Directory where state and annotated image will be saved.",
    )
    parser.add_argument(
        "--occupancy-threshold",
        type=float,
        default=0.1,
        help="Minimum bbox area ratio inside a spot to mark it occupied. Default: 0.1",
    )
    parser.add_argument(
        "--uncertain-overlap-threshold",
        type=float,
        default=float(os.getenv("PARKTWIN_UNCERTAIN_OVERLAP_THRESHOLD", "0.05")),
        help="Minimum overlap ratio to mark a spot uncertain. Default: 0.05.",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_dir = Path(args.output_dir)

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    analysis = analyze_parking_image(
        image_path=image_path,
        spots_path=args.spots,
        detector=detector,
        occupancy_threshold=args.occupancy_threshold,
        uncertain_overlap_threshold=args.uncertain_overlap_threshold,
    )

    state = build_twin_state(analysis.spots)
    state_path = output_dir / f"{image_path.stem}_state.json"
    annotated_image_path = output_dir / f"{image_path.stem}_annotated.jpg"

    save_twin_state(state, state_path)
    save_annotated_image(
        image_path,
        analysis.spots,
        analysis.detections,
        annotated_image_path,
    )

    print(f"Twin state saved to: {state_path}")
    print(f"Annotated image saved to: {annotated_image_path}")


if __name__ == "__main__":
    main()
