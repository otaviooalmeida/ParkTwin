from camera_stream.jpeg import (
    DEFAULT_USER_AGENT,
    build_frame_url,
    discover_insecam_snapshot_url,
    fetch_jpeg_frame,
)
from camera_stream.youtube import (
    DEFAULT_FORMAT_SELECTOR,
    DEFAULT_YOUTUBE_URL,
    open_video_capture,
    read_video_frame,
    resolve_youtube_stream_url,
    save_video_frame,
)

__all__ = [
    "DEFAULT_USER_AGENT",
    "build_frame_url",
    "discover_insecam_snapshot_url",
    "fetch_jpeg_frame",
    "DEFAULT_FORMAT_SELECTOR",
    "DEFAULT_YOUTUBE_URL",
    "open_video_capture",
    "read_video_frame",
    "resolve_youtube_stream_url",
    "save_video_frame",
]
