import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from twin.models import ParkingTwinState, SpotState


class TwinRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def save_state(
        self,
        state: ParkingTwinState,
        previous_state: ParkingTwinState | None = None,
        retention_snapshots: int | None = None,
    ) -> None:
        """Persist one snapshot and its status-change events atomically."""
        changed_spots = _changed_spots(state, previous_state)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO snapshots (
                    parking_lot_id,
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate,
                    spots_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.parking_lot_id,
                    state.timestamp,
                    state.total_spots,
                    state.occupied_count,
                    state.free_count,
                    state.uncertain_count,
                    state.occupancy_rate,
                    json.dumps([asdict(spot) for spot in state.spots]),
                ),
            )
            connection.executemany(
                """
                INSERT INTO spot_events (
                    parking_lot_id,
                    snapshot_timestamp,
                    spot_id,
                    status,
                    confidence
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        state.parking_lot_id,
                        state.timestamp,
                        spot.id,
                        spot.status,
                        spot.confidence,
                    )
                    for spot in changed_spots
                ],
            )
            if retention_snapshots is not None:
                self._prune_history(
                    connection,
                    parking_lot_id=state.parking_lot_id,
                    keep_snapshots=retention_snapshots,
                )

    def save_snapshot(self, state: ParkingTwinState) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO snapshots (
                    parking_lot_id,
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate,
                    spots_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.parking_lot_id,
                    state.timestamp,
                    state.total_spots,
                    state.occupied_count,
                    state.free_count,
                    state.uncertain_count,
                    state.occupancy_rate,
                    json.dumps([asdict(spot) for spot in state.spots]),
                ),
            )

    def save_spot_events(
        self,
        state: ParkingTwinState,
        previous_state: ParkingTwinState | None = None,
    ) -> None:
        changed_spots = _changed_spots(state, previous_state)
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO spot_events (
                    parking_lot_id,
                    snapshot_timestamp,
                    spot_id,
                    status,
                    confidence
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        state.parking_lot_id,
                        state.timestamp,
                        spot.id,
                        spot.status,
                        spot.confidence,
                    )
                    for spot in changed_spots
                ],
            )

    def get_latest_snapshot(
        self,
        parking_lot_id: str | None = None,
    ) -> ParkingTwinState | None:
        where_clause = "WHERE parking_lot_id = ?" if parking_lot_id is not None else ""
        parameters = (parking_lot_id,) if parking_lot_id is not None else ()
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT
                    timestamp,
                    parking_lot_id,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate,
                    spots_json
                FROM snapshots
                {where_clause}
                ORDER BY id DESC
                LIMIT 1
                """,
                parameters,
            ).fetchone()

        if row is None:
            return None

        spots = [
            SpotState(
                id=spot["id"],
                polygon=spot["polygon"],
                status=spot["status"],
                confidence=spot["confidence"],
                occupied_since=spot.get("occupied_since"),
                last_changed_at=spot.get("last_changed_at"),
                pending_status=spot.get("pending_status"),
                pending_count=int(spot.get("pending_count", 0)),
            )
            for spot in json.loads(row["spots_json"])
        ]

        return ParkingTwinState(
            timestamp=row["timestamp"],
            spots=spots,
            total_spots=row["total_spots"],
            occupied_count=row["occupied_count"],
            free_count=row["free_count"],
            uncertain_count=row["uncertain_count"],
            occupancy_rate=row["occupancy_rate"],
            parking_lot_id=row["parking_lot_id"],
        )

    def get_recent_events(
        self,
        limit: int,
        offset: int = 0,
        parking_lot_id: str | None = None,
    ) -> list[dict[str, Any]]:
        _validate_page(limit, offset)
        where_clause = "WHERE parking_lot_id = ?" if parking_lot_id is not None else ""
        parameters: list[Any] = (
            [parking_lot_id, limit, offset] if parking_lot_id is not None else [limit, offset]
        )
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    snapshot_timestamp,
                    spot_id,
                    status,
                    confidence,
                    created_at
                FROM spot_events
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    def get_occupancy_history(
        self,
        limit: int | None = None,
        offset: int = 0,
        parking_lot_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if limit is None:
            if offset != 0:
                raise ValueError("offset requires a limit")
            limit_clause = ""
            page_parameters: list[Any] = []
        else:
            _validate_page(limit, offset)
            limit_clause = "LIMIT ? OFFSET ?"
            page_parameters = [limit, offset]

        where_clause = "WHERE parking_lot_id = ?" if parking_lot_id is not None else ""
        parameters = (
            [parking_lot_id, *page_parameters] if parking_lot_id is not None else page_parameters
        )
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate
                FROM (
                    SELECT
                        id,
                        timestamp,
                        total_spots,
                        occupied_count,
                        free_count,
                        uncertain_count,
                        occupancy_rate
                    FROM snapshots
                    {where_clause}
                    ORDER BY id DESC
                    {limit_clause}
                )
                ORDER BY id ASC
                """,
                parameters,
            ).fetchall()

        return [dict(row) for row in rows]

    def _prune_history(
        self,
        connection: sqlite3.Connection,
        *,
        parking_lot_id: str | None,
        keep_snapshots: int,
    ) -> None:
        if keep_snapshots < 1:
            raise ValueError("retention_snapshots must be at least 1")
        connection.execute(
            """
            DELETE FROM snapshots
            WHERE id IN (
                SELECT id
                FROM snapshots
                WHERE parking_lot_id IS ?
                ORDER BY id DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (parking_lot_id, keep_snapshots),
        )
        connection.execute(
            """
            DELETE FROM spot_events
            WHERE parking_lot_id IS ?
              AND snapshot_timestamp NOT IN (
                  SELECT timestamp
                  FROM snapshots
                  WHERE parking_lot_id IS ?
              )
            """,
            (parking_lot_id, parking_lot_id),
        )

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parking_lot_id TEXT,
                    timestamp TEXT NOT NULL,
                    total_spots INTEGER NOT NULL,
                    occupied_count INTEGER NOT NULL,
                    free_count INTEGER NOT NULL,
                    uncertain_count INTEGER NOT NULL,
                    occupancy_rate REAL NOT NULL,
                    spots_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS spot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parking_lot_id TEXT,
                    snapshot_timestamp TEXT NOT NULL,
                    spot_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            event_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(spot_events)")
            }
            if "parking_lot_id" not in event_columns:
                connection.execute("ALTER TABLE spot_events ADD COLUMN parking_lot_id TEXT")
                connection.execute(
                    """
                    UPDATE spot_events
                    SET parking_lot_id = (
                        SELECT parking_lot_id
                        FROM snapshots
                        WHERE snapshots.timestamp = spot_events.snapshot_timestamp
                        ORDER BY snapshots.id DESC
                        LIMIT 1
                    )
                    """
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_snapshots_lot_id "
                "ON snapshots(parking_lot_id, id DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_lot_id "
                "ON spot_events(parking_lot_id, id DESC)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection


def _validate_page(limit: int, offset: int) -> None:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if offset < 0:
        raise ValueError("offset cannot be negative")


def _changed_spots(
    state: ParkingTwinState,
    previous_state: ParkingTwinState | None,
) -> list[SpotState]:
    if previous_state is None:
        return state.spots

    previous_by_id = {spot.id: spot for spot in previous_state.spots}
    return [
        spot
        for spot in state.spots
        if spot.id not in previous_by_id or previous_by_id[spot.id].status != spot.status
    ]
