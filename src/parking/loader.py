import json
from pathlib import Path

from parking.models import ParkingSpot


def load_parking_spots(path: str | Path) -> list[ParkingSpot]:
    with Path(path).open(encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Parking spots JSON must contain a list.")

    return [ParkingSpot(id=item["id"], polygon=item["polygon"]) for item in data]
