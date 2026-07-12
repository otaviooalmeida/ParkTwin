from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=EPKWu223XEg"
DEFAULT_FORMAT_SELECTOR = "best[height<=720]/best[height<=1080]/best"


def resolve_youtube_stream_url(
    youtube_url: str,
    format_selector: str = DEFAULT_FORMAT_SELECTOR,
) -> str:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as error:
        raise RuntimeError(
            "yt-dlp is required for YouTube live streams. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from error

    options = {
        "format": format_selector,
        "quiet": True,
        "no_warnings": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    stream_url = info.get("url")
    if not stream_url:
        raise ValueError(f"Could not resolve a playable stream URL for {youtube_url}")

    return str(stream_url)


def open_video_capture(stream_url: str) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(stream_url)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("Could not open YouTube stream with OpenCV.")

    return capture


def read_video_frame(capture: cv2.VideoCapture) -> np.ndarray:
    ok, frame = capture.read()
    if not ok or frame is None:
        raise RuntimeError("Could not read a frame from the video stream.")

    return frame


def save_video_frame(frame: np.ndarray, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.stem}.tmp{path.suffix}")

    if not cv2.imwrite(str(temp_path), frame):
        raise RuntimeError(f"Could not write frame to {temp_path}")

    temp_path.replace(path)
    return path
