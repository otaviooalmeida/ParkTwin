from dataclasses import dataclass
from typing import Literal


Point = list[float]
BBox = list[float]
SpotStatus = Literal["free", "occupied", "uncertain"]


@dataclass
class ParkingSpot:
    id: str
    polygon: list[Point]
    status: SpotStatus = "free"
    confidence: float | None = None

    def __post_init__(self) -> None:
        if len(self.polygon) < 3:
            raise ValueError("Parking spot polygon must have at least 3 points.")

        for point in self.polygon:
            if len(point) != 2:
                raise ValueError("Each polygon point must contain x and y coordinates.")


@dataclass
class VehicleDetection:
    bbox: BBox
    class_name: str
    confidence: float
