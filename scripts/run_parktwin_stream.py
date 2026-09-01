import argparse
import logging
import os
import sys
from pathlib import Path
from time import sleep, time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from camera_stream.jpeg import discover_insecam_snapshot_url, fetch_jpeg_frame  # noqa: E402
from detection.yolo_detector import VehicleDetector  # noqa: E402
from parktwin.pipeline import process_parking_image  # noqa: E402
from twin.repository import TwinRepository  # noqa: E402

DEFAULT_INSECAM_URL = "http://www.insecam.org/en/view/945438/"


def main() -> None:
    logging.basicConfig(level=os.getenv("PARKTWIN_LOG_LEVEL", "INFO"))
    parser = argparse.ArgumentParser(
        description="Monitor a JPEG camera stream and update ParkTwin continuously."
    )
    parser.add_argument(
        "--source-url",
        default=os.getenv("PARKTWIN_SOURCE_URL", DEFAULT_INSECAM_URL),
        help="Insecam camera page URL or direct JPEG snapshot URL.",
    )
    parser.add_argument(
        "--direct-frame-url",
        action="store_true",
        help="Treat --source-url as the direct JPEG endpoint instead of discovering it from HTML.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("PARKTWIN_INTERVAL_SECONDS", "2.0")),
        help="Seconds between processed frames. Default: 2.0.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=float(os.getenv("PARKTWIN_REQUEST_TIMEOUT", "20.0")),
        help="HTTP timeout in seconds. Default: 20.0.",
    )
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
        help="Path to the YOLO model file. Default: yolo11s.pt.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=int(os.getenv("PARKTWIN_IMGSZ", "1280")),
        help="YOLO inference image size. Default: 1280.",
    )
    parser.add_argument(
        "--occupancy-threshold",
        type=float,
        default=float(os.getenv("PARKTWIN_OCCUPANCY_THRESHOLD", "0.1")),
        help="Minimum bbox area ratio inside a spot to mark it occupied. Default: 0.1.",
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
        default=os.getenv("PARKTWIN_PARKING_LOT_ID", "insecam-945438"),
        help="Parking lot identifier stored in the twin state.",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("PARKTWIN_DB_PATH", PROJECT_ROOT / "data" / "parktwin.db"),
        help="SQLite database path. Default: data/parktwin.db.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("PARKTWIN_OUTPUTS_DIR", PROJECT_ROOT / "data" / "outputs"),
        help="Directory where latest frame and annotated image will be saved.",
    )
    parser.add_argument(
        "--draw-detections",
        action="store_true",
        help="Draw YOLO bounding boxes in addition to spot polygons.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_path = output_dir / "latest_frame.jpg"
    annotated_path = output_dir / "latest_annotated.jpg"

    snapshot_url = (
        args.source_url
        if args.direct_frame_url
        else discover_insecam_snapshot_url(
            args.source_url,
            timeout=args.request_timeout,
        )
    )

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    repository = TwinRepository(args.db)

    print(f"Frame URL: {snapshot_url}")
    print(f"Writing latest frame to: {frame_path}")
    print(f"Writing latest annotated image to: {annotated_path}")
    print(f"Writing snapshots to SQLite: {Path(args.db)}")

    while True:
        started_at = time()
        try:
            fetch_jpeg_frame(
                snapshot_url,
                frame_path,
                timeout=args.request_timeout,
            )
            result = process_parking_image(
                image_path=frame_path,
                spots_path=args.spots,
                detector=detector,
                repository=repository,
                parking_lot_id=args.parking_lot_id,
                annotated_image_path=annotated_path,
                occupancy_threshold=args.occupancy_threshold,
                uncertain_overlap_threshold=args.uncertain_overlap_threshold,
                change_confirmation_frames=args.change_confirmation_frames,
                retention_snapshots=args.retention_snapshots,
                draw_detections=args.draw_detections,
            )
            state = result.state

            print(
                f"{state.timestamp} | "
                f"{state.occupied_count}/{state.total_spots} occupied "
                f"({state.occupancy_rate:.1%})"
            )
        except KeyboardInterrupt:
            print("Stopping monitor.")
            break
        except Exception as error:
            print(f"Frame processing failed: {error}", file=sys.stderr)

        elapsed = time() - started_at
        sleep(max(args.interval - elapsed, 0.0))


if __name__ == "__main__":
    main()
