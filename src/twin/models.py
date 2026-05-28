from dataclasses import dataclass
from typing import Literal

from parking.models import Point


SpotStatus = Literal["free", "occupied", "uncertain"]


@dataclass
class SpotState:
    id: str
    polygon: list[Point]
    status: SpotStatus
    confidence: float | None = None


@dataclass
class ParkingTwinState:
    timestamp: str
    spots: list[SpotState]
    total_spots: int
    occupied_count: int
    free_count: int
    uncertain_count: int
    occupancy_rate: float


def calculate_twin_counts(spots: list[SpotState]) -> dict[str, int | float]:
    total_spots = len(spots)
    occupied_count = _count_spots_by_status(spots, "occupied")
    free_count = _count_spots_by_status(spots, "free")
    uncertain_count = _count_spots_by_status(spots, "uncertain")

    occupancy_rate = occupied_count / total_spots if total_spots > 0 else 0.0

    return {
        "total_spots": total_spots,
        "occupied_count": occupied_count,
        "free_count": free_count,
        "uncertain_count": uncertain_count,
        "occupancy_rate": occupancy_rate,
    }


def _count_spots_by_status(spots: list[SpotState], status: SpotStatus) -> int:
    return sum(1 for spot in spots if spot.status == status)
