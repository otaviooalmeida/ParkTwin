import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from parking.models import ParkingSpot


@dataclass
class TwinState:
    timestamp: str
    spots: list[ParkingSpot]
    total_spots: int
    occupied_count: int
    free_count: int
    uncertain_count: int


def build_twin_state(spots: list[ParkingSpot]) -> TwinState:
    return TwinState(
        timestamp=datetime.now(timezone.utc).isoformat(),
        spots=spots,
        total_spots=len(spots),
        occupied_count=_count_spots_by_status(spots, "occupied"),
        free_count=_count_spots_by_status(spots, "free"),
        uncertain_count=_count_spots_by_status(spots, "uncertain"),
    )


def save_twin_state(state: TwinState, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(asdict(state), file, indent=2)


def _count_spots_by_status(spots: list[ParkingSpot], status: str) -> int:
    return sum(1 for spot in spots if spot.status == status)
