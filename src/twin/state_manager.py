from datetime import UTC, datetime

from parking.models import ParkingSpot
from twin.models import ParkingTwinState, SpotState, calculate_twin_counts


def update_twin_state(
    parking_lot_id: str,
    current_spot_statuses: list[ParkingSpot | SpotState],
    previous_state: ParkingTwinState | None = None,
    change_confirmation_frames: int = 1,
) -> ParkingTwinState:
    if change_confirmation_frames < 1:
        raise ValueError("change_confirmation_frames must be at least 1")

    timestamp = datetime.now(UTC).isoformat()
    previous_spots_by_id = _index_previous_spots(previous_state)
    spot_states = [
        _build_spot_state(
            current_spot,
            previous_spots_by_id.get(current_spot.id),
            timestamp,
            change_confirmation_frames,
        )
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
    confirmation_frames: int,
) -> SpotState:
    if previous_spot is None:
        return _accepted_spot_state(current_spot, None, timestamp)

    if current_spot.status == previous_spot.status:
        return SpotState(
            id=current_spot.id,
            polygon=current_spot.polygon,
            status=current_spot.status,
            confidence=current_spot.confidence,
            occupied_since=(
                previous_spot.occupied_since
                or (previous_spot.last_changed_at if current_spot.status == "occupied" else None)
            ),
            last_changed_at=previous_spot.last_changed_at,
        )

    pending_count = (
        previous_spot.pending_count + 1
        if previous_spot.pending_status == current_spot.status
        else 1
    )
    if pending_count >= confirmation_frames:
        return _accepted_spot_state(current_spot, previous_spot, timestamp)

    return SpotState(
        id=previous_spot.id,
        polygon=current_spot.polygon,
        status=previous_spot.status,
        confidence=previous_spot.confidence,
        occupied_since=previous_spot.occupied_since,
        last_changed_at=previous_spot.last_changed_at,
        pending_status=current_spot.status,
        pending_count=pending_count,
    )


def _accepted_spot_state(
    current_spot: ParkingSpot | SpotState,
    previous_spot: SpotState | None,
    timestamp: str,
) -> SpotState:
    status_changed = previous_spot is None or current_spot.status != previous_spot.status
    occupied_since = None
    if current_spot.status == "occupied":
        if previous_spot is not None and previous_spot.status == "occupied":
            occupied_since = previous_spot.occupied_since
        else:
            occupied_since = timestamp

    return SpotState(
        id=current_spot.id,
        polygon=current_spot.polygon,
        status=current_spot.status,
        confidence=current_spot.confidence,
        occupied_since=occupied_since,
        last_changed_at=timestamp if status_changed else previous_spot.last_changed_at,
    )
