import argparse
import logging
import os
import sys
from pathlib import Path
from time import sleep, time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from camera_stream.youtube import (  # noqa: E402
    DEFAULT_FORMAT_SELECTOR,
    DEFAULT_YOUTUBE_URL,
    open_video_capture,
    read_video_frame,
    resolve_youtube_stream_url,
    save_video_frame,
)
from detection.yolo_detector import VehicleDetector  # noqa: E402
from parktwin.pipeline import process_parking_image  # noqa: E402
from twin.repository import TwinRepository  # noqa: E402


def main() -> None:
    logging.basicConfig(level=os.getenv("PARKTWIN_LOG_LEVEL", "INFO"))
    parser = argparse.ArgumentParser(
        description="Monitor a YouTube live stream and update ParkTwin continuously."
    )
    parser.add_argument(
        "--youtube-url",
        default=os.getenv("PARKTWIN_YOUTUBE_URL", DEFAULT_YOUTUBE_URL),
        help=f"YouTube live URL. Default: {DEFAULT_YOUTUBE_URL}",
    )
    parser.add_argument(
        "--format",
        default=DEFAULT_FORMAT_SELECTOR,
        help=f"yt-dlp format selector. Default: {DEFAULT_FORMAT_SELECTOR}",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("PARKTWIN_INTERVAL_SECONDS", "5.0")),
        help="Seconds between processed frames. Default: 5.0.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Stop after processing this many frames. Default: run forever.",
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
        default=os.getenv("PARKTWIN_PARKING_LOT_ID", "youtube-live"),
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

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    repository = TwinRepository(args.db)
    capture = _open_youtube_capture(args.youtube_url, args.format)
    processed_frames = 0

    print(f"YouTube URL: {args.youtube_url}")
    print(f"Format selector: {args.format}")
    print(f"Processing interval: {args.interval}s")
    print(f"Writing latest frame to: {frame_path}")
    print(f"Writing latest annotated image to: {annotated_path}")
    print(f"Writing snapshots to SQLite: {Path(args.db)}")

    try:
        while args.max_frames is None or processed_frames < args.max_frames:
            started_at = time()
            try:
                frame = read_video_frame(capture)
            except Exception as error:
                print(f"Stream read failed, reopening: {error}", file=sys.stderr)
                capture.release()
                sleep(2.0)
                capture = _open_youtube_capture(args.youtube_url, args.format)
                continue

            try:
                save_video_frame(frame, frame_path)
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

                processed_frames += 1
                print(
                    f"{state.timestamp} | frame {processed_frames} | "
                    f"{state.occupied_count}/{state.total_spots} occupied "
                    f"({state.occupancy_rate:.1%})"
                )
            except Exception as error:
                print(f"Frame processing failed: {error}", file=sys.stderr)

            elapsed = time() - started_at
            sleep(max(args.interval - elapsed, 0.0))
    except KeyboardInterrupt:
        print("Stopping monitor.")
    finally:
        capture.release()


def _open_youtube_capture(youtube_url: str, format_selector: str):
    stream_url = resolve_youtube_stream_url(youtube_url, format_selector)
    return open_video_capture(stream_url)


if __name__ == "__main__":
    main()
