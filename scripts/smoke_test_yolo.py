"""Run one end-to-end inference with the real YOLO model."""

import argparse
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from detection.yolo_detector import VehicleDetector  # noqa: E402
from parktwin.pipeline import process_parking_image  # noqa: E402
from twin.repository import TwinRepository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test the real YOLO pipeline.")
    parser.add_argument("--model", default="yolo11s.pt")
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    image_path = PROJECT_ROOT / "data" / "samples" / "baseline.jpg"
    spots_path = PROJECT_ROOT / "data" / "samples" / "spots_annotated.json"

    with TemporaryDirectory(prefix="parktwin-smoke-") as temporary_directory:
        output_dir = Path(temporary_directory)
        repository = TwinRepository(output_dir / "parktwin.db")
        result = process_parking_image(
            image_path=image_path,
            spots_path=spots_path,
            detector=VehicleDetector(args.model, imgsz=args.imgsz),
            repository=repository,
            parking_lot_id="ci-smoke",
            annotated_image_path=output_dir / "latest_annotated.jpg",
            occupancy_threshold=0.1,
            uncertain_overlap_threshold=0.05,
            change_confirmation_frames=1,
            retention_snapshots=5,
        )
        persisted_state = repository.get_latest_snapshot("ci-smoke")

        if persisted_state != result.state:
            raise RuntimeError("Persisted state differs from the processed state.")
        if result.state.total_spots == 0:
            raise RuntimeError("Smoke test loaded no parking spots.")
        if not result.annotated_image_path.is_file():
            raise RuntimeError("Annotated image was not generated.")
        if result.processing_time_ms <= 0:
            raise RuntimeError("Invalid processing duration.")

        print(
            "YOLO smoke test passed: "
            f"{len(result.analysis.detections)} detections, "
            f"{result.state.total_spots} spots, "
            f"{result.processing_time_ms:.1f} ms"
        )


if __name__ == "__main__":
    main()
