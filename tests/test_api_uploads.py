from io import BytesIO

import cv2
import numpy as np
import pytest

from api.uploads import InvalidImageUpload, UploadTooLarge, save_validated_image


def test_save_validated_image_normalizes_and_publishes_jpeg(tmp_path):
    ok, encoded = cv2.imencode(".png", np.zeros((20, 30, 3), dtype=np.uint8))
    assert ok
    destination = tmp_path / "uploads" / "image.jpg"

    result = save_validated_image(
        BytesIO(encoded.tobytes()),
        destination,
        max_bytes=1024 * 1024,
    )

    assert result == destination
    assert destination.read_bytes().startswith(b"\xff\xd8")
    assert cv2.imread(str(destination)).shape[:2] == (20, 30)
    assert not list(destination.parent.glob(".*"))


def test_save_validated_image_rejects_invalid_content(tmp_path):
    with pytest.raises(InvalidImageUpload, match="not a valid image"):
        save_validated_image(
            BytesIO(b"not-an-image"),
            tmp_path / "image.jpg",
            max_bytes=1024,
        )


def test_save_validated_image_enforces_size_limit_and_cleans_temporary_files(tmp_path):
    destination = tmp_path / "image.jpg"

    with pytest.raises(UploadTooLarge, match="upload limit"):
        save_validated_image(BytesIO(b"x" * 20), destination, max_bytes=10)

    assert not destination.exists()
    assert not list(tmp_path.glob(".*"))
