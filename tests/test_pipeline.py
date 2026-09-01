import json
import sqlite3

import cv2
import numpy as np

from parking.models import VehicleDetection
from parktwin.pipeline import analyze_parking_image, process_parking_image
from twin.repository import TwinRepository


class StubDetector:
    def __init__(self, detections):
        self.detections = detections
        self.calls = []

    def detect(self, image_path):
        self.calls.append(image_path)
        return self.detections


def test_analyze_parking_image_uses_configured_threshold(tmp_path):
    spots_path = _write_spots(tmp_path)
    detector = StubDetector(
        [VehicleDetection(bbox=[10, 10, 30, 30], class_name="car", confidence=0.9)]
    )

    analysis = analyze_parking_image(
        tmp_path / "frame.jpg",
        spots_path,
        detector,
        occupancy_threshold=0.5,
    )

    assert analysis.spots[0].status == "occupied"
    assert analysis.detections == detector.detections
    assert detector.calls == [tmp_path / "frame.jpg"]


def test_process_parking_image_persists_changes_and_publishes_image(tmp_path):
    image_path = tmp_path / "frame.jpg"
    assert cv2.imwrite(str(image_path), np.zeros((40, 40, 3), dtype=np.uint8))
    spots_path = _write_spots(tmp_path)
    output_path = tmp_path / "outputs" / "latest_annotated.jpg"
    repository = TwinRepository(tmp_path / "parktwin.db")
    detector = StubDetector(
        [VehicleDetection(bbox=[10, 10, 30, 30], class_name="car", confidence=0.9)]
    )

    first = process_parking_image(
        image_path,
        spots_path,
        detector,
        repository,
        "lot-1",
        output_path,
        occupancy_threshold=0.5,
    )
    process_parking_image(
        image_path,
        spots_path,
        detector,
        repository,
        "lot-1",
        output_path,
        occupancy_threshold=0.5,
    )

    assert first.state.occupied_count == 1
    assert output_path.exists()
    assert cv2.imread(str(output_path)) is not None
    assert len(repository.get_occupancy_history()) == 2
    with sqlite3.connect(repository.db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM spot_events").fetchone()[0] == 1
    assert not list(output_path.parent.glob(".*.tmp.jpg"))


def _write_spots(tmp_path):
    path = tmp_path / "spots.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "A1",
                    "polygon": [[0, 0], [40, 0], [40, 40], [0, 40]],
                }
            ]
        ),
        encoding="utf-8",
    )
    return path
