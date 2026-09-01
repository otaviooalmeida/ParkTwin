import sqlite3

import pytest

from twin.models import ParkingTwinState, SpotState
from twin.repository import TwinRepository


def test_save_state_records_only_status_changes(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    previous = _state("2026-01-01T10:00:00+00:00", "free")
    current = _state("2026-01-01T10:01:00+00:00", "occupied")

    repository.save_state(previous)
    repository.save_state(current, previous)

    events = repository.get_recent_events(limit=10)
    assert [(event["spot_id"], event["status"]) for event in events] == [
        ("A1", "occupied"),
        ("A1", "free"),
    ]
    assert len(repository.get_occupancy_history()) == 2


def test_save_state_skips_events_when_status_does_not_change(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    previous = _state("2026-01-01T10:00:00+00:00", "occupied", confidence=0.8)
    current = _state("2026-01-01T10:01:00+00:00", "occupied", confidence=0.9)

    repository.save_state(previous)
    repository.save_state(current, previous)

    events = repository.get_recent_events(limit=10)
    assert len(events) == 1
    assert events[0]["confidence"] == 0.8


def test_latest_snapshot_can_be_scoped_to_parking_lot(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    lot_one = _state("2026-01-01T10:00:00+00:00", "free")
    lot_two = _state("2026-01-01T10:01:00+00:00", "occupied")
    lot_two.parking_lot_id = "lot-2"
    repository.save_state(lot_one)
    repository.save_state(lot_two)

    assert repository.get_latest_snapshot("lot-1") == lot_one
    assert repository.get_latest_snapshot("lot-2") == lot_two


def test_save_state_rolls_back_snapshot_when_event_insert_fails(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER reject_events
            BEFORE INSERT ON spot_events
            BEGIN
                SELECT RAISE(ABORT, 'event rejected');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="event rejected"):
        repository.save_state(_state("2026-01-01T10:00:00+00:00", "free"))

    assert repository.get_latest_snapshot() is None


def _state(
    timestamp: str,
    status: str,
    confidence: float | None = None,
) -> ParkingTwinState:
    spot = SpotState(
        id="A1",
        polygon=[[0, 0], [20, 0], [20, 20], [0, 20]],
        status=status,
        confidence=confidence,
    )
    return ParkingTwinState(
        timestamp=timestamp,
        spots=[spot],
        total_spots=1,
        occupied_count=int(status == "occupied"),
        free_count=int(status == "free"),
        uncertain_count=int(status == "uncertain"),
        occupancy_rate=float(status == "occupied"),
        parking_lot_id="lot-1",
    )
