import sqlite3

from twin.models import ParkingTwinState, SpotState
from twin.repository import TwinRepository


def test_repository_creates_tables(tmp_path):
    db_path = tmp_path / "parktwin.db"

    TwinRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert "snapshots" in table_names
    assert "spot_events" in table_names


def test_save_and_get_latest_snapshot(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    first_state = _state("2026-05-28T10:00:00+00:00", occupied_count=1)
    latest_state = _state("2026-05-28T10:05:00+00:00", occupied_count=2)

    repository.save_snapshot(first_state)
    repository.save_snapshot(latest_state)

    assert repository.get_latest_snapshot() == latest_state


def test_get_latest_snapshot_returns_none_without_snapshots(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")

    assert repository.get_latest_snapshot() is None


def test_save_spot_events_and_get_recent_events(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    state = _state("2026-05-28T10:00:00+00:00", occupied_count=1)

    repository.save_spot_events(state)

    events = repository.get_recent_events(limit=2)
    assert len(events) == 2
    assert events[0]["snapshot_timestamp"] == state.timestamp
    assert events[0]["spot_id"] == "A2"
    assert events[0]["status"] == "occupied"
    assert events[0]["confidence"] == 0.9
    assert events[1]["spot_id"] == "A1"
    assert events[1]["status"] == "free"


def test_get_occupancy_history_returns_snapshots_in_insert_order(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    first_state = _state("2026-05-28T10:00:00+00:00", occupied_count=1)
    second_state = _state("2026-05-28T10:05:00+00:00", occupied_count=2)

    repository.save_snapshot(first_state)
    repository.save_snapshot(second_state)

    history = repository.get_occupancy_history()

    assert history == [
        {
            "timestamp": first_state.timestamp,
            "total_spots": 2,
            "occupied_count": 1,
            "free_count": 1,
            "uncertain_count": 0,
            "occupancy_rate": 0.5,
        },
        {
            "timestamp": second_state.timestamp,
            "total_spots": 2,
            "occupied_count": 2,
            "free_count": 0,
            "uncertain_count": 0,
            "occupancy_rate": 1.0,
        },
    ]


def _state(timestamp: str, occupied_count: int) -> ParkingTwinState:
    spots = [
        SpotState(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        SpotState(
            id="A2",
            polygon=[[20, 0], [30, 0], [30, 10]],
            status="occupied",
            confidence=0.9,
        ),
    ]

    if occupied_count == 2:
        spots[0].status = "occupied"
        spots[0].confidence = 0.8

    return ParkingTwinState(
        timestamp=timestamp,
        spots=spots,
        total_spots=2,
        occupied_count=occupied_count,
        free_count=2 - occupied_count,
        uncertain_count=0,
        occupancy_rate=occupied_count / 2,
    )
