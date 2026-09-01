import sqlite3

from twin.models import ParkingTwinState, SpotState
from twin.repository import TwinRepository


def test_history_pagination_returns_selected_window_in_chronological_order(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    previous = None
    states = []
    for index in range(5):
        state = _state(index, "lot-1", "occupied" if index % 2 else "free")
        repository.save_state(state, previous)
        states.append(state)
        previous = state

    rows = repository.get_occupancy_history(
        limit=2,
        offset=1,
        parking_lot_id="lot-1",
    )

    assert [row["timestamp"] for row in rows] == [
        states[2].timestamp,
        states[3].timestamp,
    ]


def test_events_support_parking_lot_filter_and_offset(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    lot_one_first = _state(0, "lot-1", "free")
    lot_one_second = _state(1, "lot-1", "occupied")
    lot_two = _state(2, "lot-2", "occupied")
    repository.save_state(lot_one_first)
    repository.save_state(lot_one_second, lot_one_first)
    repository.save_state(lot_two)

    rows = repository.get_recent_events(
        limit=1,
        offset=1,
        parking_lot_id="lot-1",
    )

    assert len(rows) == 1
    assert rows[0]["snapshot_timestamp"] == lot_one_first.timestamp


def test_retention_prunes_only_target_parking_lot_and_orphaned_events(tmp_path):
    repository = TwinRepository(tmp_path / "parktwin.db")
    previous = None
    states = []
    for index in range(4):
        state = _state(index, "lot-1", "occupied" if index % 2 else "free")
        repository.save_state(state, previous, retention_snapshots=2)
        previous = state
        states.append(state)
    other_lot = _state(10, "lot-2", "free")
    repository.save_state(other_lot, retention_snapshots=2)

    lot_one_history = repository.get_occupancy_history(parking_lot_id="lot-1")
    lot_one_events = repository.get_recent_events(10, parking_lot_id="lot-1")

    assert [row["timestamp"] for row in lot_one_history] == [
        states[2].timestamp,
        states[3].timestamp,
    ]
    assert {row["snapshot_timestamp"] for row in lot_one_events} == {
        states[2].timestamp,
        states[3].timestamp,
    }
    assert repository.get_latest_snapshot("lot-2") == other_lot


def test_repository_migrates_legacy_events_table(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE spot_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_timestamp TEXT NOT NULL,
                spot_id TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    TwinRepository(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(spot_events)")}
    assert "parking_lot_id" in columns


def _state(index, parking_lot_id, status):
    spot = SpotState(
        id="A1",
        polygon=[[0, 0], [10, 0], [10, 10]],
        status=status,
    )
    return ParkingTwinState(
        timestamp=f"2026-01-01T10:{index:02d}:00+00:00",
        spots=[spot],
        total_spots=1,
        occupied_count=int(status == "occupied"),
        free_count=int(status == "free"),
        uncertain_count=0,
        occupancy_rate=float(status == "occupied"),
        parking_lot_id=parking_lot_id,
    )
