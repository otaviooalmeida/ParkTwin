from parking.models import ParkingSpot
from twin.models import ParkingTwinState, SpotState
from twin.state_manager import update_twin_state


def test_update_twin_state_builds_parking_twin_state_from_current_spots():
    current_spots = [
        ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        ParkingSpot(
            id="A2",
            polygon=[[20, 0], [30, 0], [30, 10]],
            status="occupied",
            confidence=0.9,
        ),
    ]

    state = update_twin_state("lot-1", current_spots)

    assert state.parking_lot_id == "lot-1"
    assert state.total_spots == 2
    assert state.occupied_count == 1
    assert state.free_count == 1
    assert state.uncertain_count == 0
    assert state.occupancy_rate == 0.5
    assert state.spots[0].last_changed_at == state.timestamp
    assert state.spots[0].occupied_since is None
    assert state.spots[1].last_changed_at == state.timestamp
    assert state.spots[1].occupied_since == state.timestamp


def test_update_twin_state_preserves_occupied_since_when_spot_stays_occupied():
    previous_state = _previous_state(
        spots=[
            SpotState(
                id="A1",
                polygon=[[0, 0], [10, 0], [10, 10]],
                status="occupied",
                confidence=0.8,
                occupied_since="2026-05-28T10:00:00+00:00",
                last_changed_at="2026-05-28T10:00:00+00:00",
            )
        ]
    )
    current_spots = [
        ParkingSpot(
            id="A1",
            polygon=[[0, 0], [10, 0], [10, 10]],
            status="occupied",
            confidence=0.9,
        )
    ]

    state = update_twin_state("lot-1", current_spots, previous_state)

    assert state.spots[0].occupied_since == "2026-05-28T10:00:00+00:00"
    assert state.spots[0].last_changed_at == "2026-05-28T10:00:00+00:00"
    assert state.spots[0].confidence == 0.9


def test_update_twin_state_updates_last_changed_at_only_when_status_changes():
    previous_state = _previous_state(
        spots=[
            SpotState(
                id="A1",
                polygon=[[0, 0], [10, 0], [10, 10]],
                status="free",
                last_changed_at="2026-05-28T10:00:00+00:00",
            ),
            SpotState(
                id="A2",
                polygon=[[20, 0], [30, 0], [30, 10]],
                status="occupied",
                occupied_since="2026-05-28T10:01:00+00:00",
                last_changed_at="2026-05-28T10:01:00+00:00",
            ),
        ]
    )
    current_spots = [
        ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        ParkingSpot(id="A2", polygon=[[20, 0], [30, 0], [30, 10]], status="free"),
    ]

    state = update_twin_state("lot-1", current_spots, previous_state)

    assert state.spots[0].last_changed_at == "2026-05-28T10:00:00+00:00"
    assert state.spots[1].last_changed_at == state.timestamp
    assert state.spots[1].occupied_since is None


def test_update_twin_state_sets_occupied_since_when_spot_becomes_occupied():
    previous_state = _previous_state(
        spots=[
            SpotState(
                id="A1",
                polygon=[[0, 0], [10, 0], [10, 10]],
                status="free",
                last_changed_at="2026-05-28T10:00:00+00:00",
            )
        ]
    )
    current_spots = [
        ParkingSpot(
            id="A1",
            polygon=[[0, 0], [10, 0], [10, 10]],
            status="occupied",
            confidence=0.95,
        )
    ]

    state = update_twin_state("lot-1", current_spots, previous_state)

    assert state.spots[0].occupied_since == state.timestamp
    assert state.spots[0].last_changed_at == state.timestamp


def test_update_twin_state_requires_consecutive_frames_before_change():
    initial = update_twin_state(
        "lot-1",
        [ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free")],
        change_confirmation_frames=2,
    )
    first_detection = update_twin_state(
        "lot-1",
        [ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="occupied")],
        initial,
        change_confirmation_frames=2,
    )
    confirmed = update_twin_state(
        "lot-1",
        [ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="occupied")],
        first_detection,
        change_confirmation_frames=2,
    )

    assert first_detection.spots[0].status == "free"
    assert first_detection.spots[0].pending_status == "occupied"
    assert first_detection.spots[0].pending_count == 1
    assert confirmed.spots[0].status == "occupied"
    assert confirmed.spots[0].pending_status is None
    assert confirmed.spots[0].pending_count == 0
    assert confirmed.spots[0].last_changed_at == confirmed.timestamp


def test_update_twin_state_resets_pending_change_when_signal_recovers():
    previous = _previous_state(
        spots=[
            SpotState(
                id="A1",
                polygon=[[0, 0], [10, 0], [10, 10]],
                status="free",
                last_changed_at="2026-05-28T10:00:00+00:00",
                pending_status="occupied",
                pending_count=1,
            )
        ]
    )

    state = update_twin_state(
        "lot-1",
        [ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free")],
        previous,
        change_confirmation_frames=2,
    )

    assert state.spots[0].status == "free"
    assert state.spots[0].pending_status is None
    assert state.spots[0].pending_count == 0


def _previous_state(spots: list[SpotState]) -> ParkingTwinState:
    occupied_count = sum(1 for spot in spots if spot.status == "occupied")
    free_count = sum(1 for spot in spots if spot.status == "free")
    uncertain_count = sum(1 for spot in spots if spot.status == "uncertain")

    return ParkingTwinState(
        timestamp="2026-05-28T10:02:00+00:00",
        spots=spots,
        total_spots=len(spots),
        occupied_count=occupied_count,
        free_count=free_count,
        uncertain_count=uncertain_count,
        occupancy_rate=occupied_count / len(spots) if spots else 0.0,
        parking_lot_id="lot-1",
    )
