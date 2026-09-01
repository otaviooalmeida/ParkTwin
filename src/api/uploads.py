"""Validation and normalized storage for uploaded images."""

from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import cv2


class InvalidImageUpload(ValueError):
    pass


class UploadTooLarge(InvalidImageUpload):
    pass


def save_validated_image(
    source: BinaryIO,
    destination: str | Path,
    *,
    max_bytes: int,
) -> Path:
    """Validate image bytes and atomically store a normalized JPEG."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    raw_path = path.with_name(f".{path.name}.{token}.upload")
    normalized_path = path.with_name(f".{path.stem}.{token}.tmp{path.suffix}")
    written = 0

    try:
        with raw_path.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise UploadTooLarge(f"Image exceeds the {max_bytes}-byte upload limit.")
                output.write(chunk)

        image = cv2.imread(str(raw_path))
        if image is None:
            raise InvalidImageUpload("Uploaded content is not a valid image.")
        if not cv2.imwrite(str(normalized_path), image):
            raise InvalidImageUpload("Uploaded image could not be normalized.")

        normalized_path.replace(path)
        return path
    finally:
        raw_path.unlink(missing_ok=True)
        normalized_path.unlink(missing_ok=True)
