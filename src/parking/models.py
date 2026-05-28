from dataclasses import dataclass


Point = list[float]


@dataclass
class ParkingSpot:
    id: str
    polygon: list[Point]

    def __post_init__(self) -> None:
        if len(self.polygon) < 3:
            raise ValueError("Parking spot polygon must have at least 3 points.")

        for point in self.polygon:
            if len(point) != 2:
                raise ValueError("Each polygon point must contain x and y coordinates.")
