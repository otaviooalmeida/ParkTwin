import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from detection.yolo_detector import VehicleDetector  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run vehicle detection on an image.")
    parser.add_argument("image_path", help="Path to the image file.")
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Path to the YOLO model file. Default: yolov8n.pt",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=None,
        help="YOLO inference image size.",
    )
    args = parser.parse_args()

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    detections = detector.detect(args.image_path)

    print(json.dumps([asdict(detection) for detection in detections], indent=2))


if __name__ == "__main__":
    main()
