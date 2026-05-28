from pathlib import Path

import cv2
import numpy as np

from parking.models import ParkingSpot, VehicleDetection


STATUS_COLORS = {
    "free": (0, 180, 0),
    "occupied": (0, 0, 220),
    "uncertain": (0, 180, 220),
}
DETECTION_COLOR = (220, 120, 0)


def save_annotated_image(
    image: str | Path | np.ndarray,
    spots: list[ParkingSpot],
    detections: list[VehicleDetection],
    output_path: str | Path,
) -> Path:
    annotated_image = _load_image(image).copy()

    for spot in spots:
        _draw_spot(annotated_image, spot)

    for detection in detections:
        _draw_detection(annotated_image, detection)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), annotated_image)

    return path


def _load_image(image: str | Path | np.ndarray) -> np.ndarray:
    if isinstance(image, np.ndarray):
        return image

    loaded_image = cv2.imread(str(image))
    if loaded_image is None:
        raise ValueError(f"Could not load image: {image}")

    return loaded_image


def _draw_spot(image: np.ndarray, spot: ParkingSpot) -> None:
    points = np.array(spot.polygon, dtype=np.int32).reshape((-1, 1, 2))
    color = STATUS_COLORS.get(spot.status, STATUS_COLORS["uncertain"])

    cv2.polylines(image, [points], isClosed=True, color=color, thickness=2)

    label_position = tuple(points[0][0])
    cv2.putText(
        image,
        f"{spot.id}: {spot.status}",
        label_position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )


def _draw_detection(image: np.ndarray, detection: VehicleDetection) -> None:
    x1, y1, x2, y2 = [int(value) for value in detection.bbox]
    label = f"{detection.class_name} {detection.confidence:.2f}"

    cv2.rectangle(image, (x1, y1), (x2, y2), DETECTION_COLOR, 2)
    cv2.putText(
        image,
        label,
        (x1, max(y1 - 8, 0)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        DETECTION_COLOR,
        2,
        cv2.LINE_AA,
    )
