import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from parking.models import ParkingSpot
from twin.models import ParkingTwinState, SpotState, calculate_twin_counts


TwinState = ParkingTwinState


def build_twin_state(spots: list[ParkingSpot]) -> TwinState:
    spot_states = [
        SpotState(
            id=spot.id,
            polygon=spot.polygon,
            status=spot.status,
            confidence=spot.confidence,
        )
        for spot in spots
    ]
    counts = calculate_twin_counts(spot_states)

    return ParkingTwinState(
        timestamp=datetime.now(timezone.utc).isoformat(),
        spots=spot_states,
        total_spots=int(counts["total_spots"]),
        occupied_count=int(counts["occupied_count"]),
        free_count=int(counts["free_count"]),
        uncertain_count=int(counts["uncertain_count"]),
        occupancy_rate=float(counts["occupancy_rate"]),
    )


def save_twin_state(state: TwinState, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(asdict(state), file, indent=2)
