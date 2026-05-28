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

    def save_snapshot(self, state: ParkingTwinState) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO snapshots (
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate,
                    spots_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.timestamp,
                    state.total_spots,
                    state.occupied_count,
                    state.free_count,
                    state.uncertain_count,
                    state.occupancy_rate,
                    json.dumps([asdict(spot) for spot in state.spots]),
                ),
            )

    def save_spot_events(self, state: ParkingTwinState) -> None:
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO spot_events (
                    snapshot_timestamp,
                    spot_id,
                    status,
                    confidence
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        state.timestamp,
                        spot.id,
                        spot.status,
                        spot.confidence,
                    )
                    for spot in state.spots
                ],
            )

    def get_latest_snapshot(self) -> ParkingTwinState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate,
                    spots_json
                FROM snapshots
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        if row is None:
            return None

        spots = [
            SpotState(
                id=spot["id"],
                polygon=spot["polygon"],
                status=spot["status"],
                confidence=spot["confidence"],
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
        )

    def get_recent_events(self, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    snapshot_timestamp,
                    spot_id,
                    status,
                    confidence,
                    created_at
                FROM spot_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_occupancy_history(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    timestamp,
                    total_spots,
                    occupied_count,
                    free_count,
                    uncertain_count,
                    occupancy_rate
                FROM snapshots
                ORDER BY id ASC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    snapshot_timestamp TEXT NOT NULL,
                    spot_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
