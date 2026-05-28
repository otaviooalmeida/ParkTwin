from datetime import datetime, timezone
from parking.models import ParkingSpot
from twin.models import ParkingTwinState, SpotState, calculate_twin_counts


def update_twin_state(
    parking_lot_id: str,
    current_spot_statuses: list[ParkingSpot | SpotState],
    previous_state: ParkingTwinState | None = None,
) -> ParkingTwinState:
    timestamp = datetime.now(timezone.utc).isoformat()
    previous_spots_by_id = _index_previous_spots(previous_state)
    spot_states = [
        _build_spot_state(current_spot, previous_spots_by_id.get(current_spot.id), timestamp)
        for current_spot in current_spot_statuses
    ]
    counts = calculate_twin_counts(spot_states)

    return ParkingTwinState(
        timestamp=timestamp,
        spots=spot_states,
        total_spots=int(counts["total_spots"]),
        occupied_count=int(counts["occupied_count"]),
        free_count=int(counts["free_count"]),
        uncertain_count=int(counts["uncertain_count"]),
        occupancy_rate=float(counts["occupancy_rate"]),
        parking_lot_id=parking_lot_id,
    )


def _index_previous_spots(
    previous_state: ParkingTwinState | None,
) -> dict[str, SpotState]:
    if previous_state is None:
        return {}

    return {spot.id: spot for spot in previous_state.spots}


def _build_spot_state(
    current_spot: ParkingSpot | SpotState,
    previous_spot: SpotState | None,
    timestamp: str,
) -> SpotState:
    status_changed = previous_spot is None or current_spot.status != previous_spot.status
    last_changed_at = timestamp if status_changed else previous_spot.last_changed_at

    occupied_since = _get_occupied_since(current_spot, previous_spot, timestamp)

    return SpotState(
        id=current_spot.id,
        polygon=current_spot.polygon,
        status=current_spot.status,
        confidence=current_spot.confidence,
        occupied_since=occupied_since,
        last_changed_at=last_changed_at,
    )


def _get_occupied_since(
    current_spot: ParkingSpot | SpotState,
    previous_spot: SpotState | None,
    timestamp: str,
) -> str | None:
    if current_spot.status != "occupied":
        return None

    if previous_spot is None or previous_spot.status != "occupied":
        return timestamp

    return previous_spot.occupied_since or previous_spot.last_changed_at or timestamp
