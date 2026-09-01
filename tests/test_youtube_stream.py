import sys

import numpy as np
import pytest

from camera_stream.youtube import resolve_youtube_stream_url, save_video_frame


def test_resolve_youtube_stream_url_requires_yt_dlp(monkeypatch):
    monkeypatch.setitem(sys.modules, "yt_dlp", None)

    with pytest.raises(RuntimeError, match="yt-dlp is required"):
        resolve_youtube_stream_url("https://www.youtube.com/watch?v=EPKWu223XEg")


def test_save_video_frame_writes_jpeg(tmp_path):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    output_path = tmp_path / "frame.jpg"

    saved_path = save_video_frame(frame, output_path)

    assert saved_path == output_path
    assert output_path.read_bytes().startswith(b"\xff\xd8")
