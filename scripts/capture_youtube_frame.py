import argparse
import sys
from pathlib import Path


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture one frame from a YouTube live stream."
    )
    parser.add_argument(
        "--youtube-url",
        default=DEFAULT_YOUTUBE_URL,
        help=f"YouTube live URL. Default: {DEFAULT_YOUTUBE_URL}",
    )
    parser.add_argument(
        "--format",
        default=DEFAULT_FORMAT_SELECTOR,
        help=f"yt-dlp format selector. Default: {DEFAULT_FORMAT_SELECTOR}",
    )
    parser.add_argument(
        "--output",
        default=PROJECT_ROOT / "data" / "samples" / "youtube_live_base.jpg",
        help="Output image path. Default: data/samples/youtube_live_base.jpg",
    )
    args = parser.parse_args()

    stream_url = resolve_youtube_stream_url(args.youtube_url, args.format)
    capture = open_video_capture(stream_url)
    try:
        frame = read_video_frame(capture)
    finally:
        capture.release()

    output_path = save_video_frame(frame, args.output)
    print(f"Captured frame saved to: {output_path}")


if __name__ == "__main__":
    main()
