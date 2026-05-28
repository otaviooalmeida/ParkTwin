import json

import pytest

from parking.loader import load_parking_spots
from parking.models import ParkingSpot


def test_load_parking_spots_from_json(tmp_path):
    spots_file = tmp_path / "spots.json"
    spots_file.write_text(
        json.dumps(
            [
                {
                    "id": "A1",
                    "polygon": [[10, 10], [110, 10], [110, 80], [10, 80]],
                },
                {
                    "id": "A2",
                    "polygon": [[120, 10], [220, 10], [220, 80], [120, 80]],
                },
            ]
        ),
        encoding="utf-8",
    )

    spots = load_parking_spots(spots_file)

    assert spots == [
        ParkingSpot(id="A1", polygon=[[10, 10], [110, 10], [110, 80], [10, 80]]),
        ParkingSpot(id="A2", polygon=[[120, 10], [220, 10], [220, 80], [120, 80]]),
    ]


def test_load_parking_spots_requires_json_list(tmp_path):
    spots_file = tmp_path / "spots.json"
    spots_file.write_text(json.dumps({"id": "A1", "polygon": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a list"):
        load_parking_spots(spots_file)


def test_load_parking_spots_requires_polygon_with_at_least_three_points(tmp_path):
    spots_file = tmp_path / "spots.json"
    spots_file.write_text(
        json.dumps([{"id": "A1", "polygon": [[10, 10], [110, 10]]}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least 3 points"):
        load_parking_spots(spots_file)


def test_load_parking_spots_requires_points_with_two_coordinates(tmp_path):
    spots_file = tmp_path / "spots.json"
    spots_file.write_text(
        json.dumps([{"id": "A1", "polygon": [[10, 10], [110], [110, 80]]}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="x and y coordinates"):
        load_parking_spots(spots_file)
