import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.config import get_settings
from api.schemas import (
    HealthResponse,
    OccupancyHistoryRow,
    SnapshotResponse,
    SpotEventResponse,
)
from twin.repository import TwinRepository


settings = get_settings()

app = FastAPI(
    title="ParkTwin API",
    description="HTTP API for parking occupancy snapshots, events, and latest imagery.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        database_exists=settings.db_path.exists(),
        latest_image_exists=_find_latest_annotated_image(settings.outputs_dir)
        is not None,
    )


@app.get("/api/snapshots/latest", response_model=SnapshotResponse)
def latest_snapshot() -> SnapshotResponse:
    snapshot = _load_latest_snapshot(settings.db_path, settings.outputs_dir)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No snapshot found.")

    return SnapshotResponse(**snapshot)


@app.get("/api/history", response_model=list[OccupancyHistoryRow])
def occupancy_history() -> list[OccupancyHistoryRow]:
    rows = _load_occupancy_history(settings.db_path, settings.outputs_dir)
    return [OccupancyHistoryRow(**row) for row in rows]


@app.get("/api/events", response_model=list[SpotEventResponse])
def recent_events(
    limit: int = Query(default=100, ge=1, le=500),
) -> list[SpotEventResponse]:
    rows = _load_recent_events(settings.db_path, settings.outputs_dir, limit)
    return [SpotEventResponse(**row) for row in rows]


@app.get("/api/images/latest")
def latest_annotated_image() -> FileResponse:
    image_path = _find_latest_annotated_image(settings.outputs_dir)
    if image_path is None:
        raise HTTPException(status_code=404, detail="No annotated image found.")

    return FileResponse(image_path, media_type="image/jpeg")


def _load_latest_snapshot(
    db_path: Path,
    outputs_dir: Path,
) -> dict[str, Any] | None:
    if db_path.exists():
        snapshot = TwinRepository(db_path).get_latest_snapshot()
        if snapshot is not None:
            return asdict(snapshot)

    latest_state_path = _find_latest_state_file(outputs_dir)
    if latest_state_path is None:
        return None

    return _load_state_json(latest_state_path)


def _load_occupancy_history(
    db_path: Path,
    outputs_dir: Path,
) -> list[dict[str, Any]]:
    if db_path.exists():
        history = TwinRepository(db_path).get_occupancy_history()
        if history:
            return history

    return [
        _history_row_from_state(_load_state_json(path))
        for path in sorted(
            outputs_dir.glob("*_state.json"),
            key=lambda item: item.stat().st_mtime,
        )
    ]


def _load_recent_events(
    db_path: Path,
    outputs_dir: Path,
    limit: int,
) -> list[dict[str, Any]]:
    if db_path.exists():
        events = TwinRepository(db_path).get_recent_events(limit)
        if events:
            return events

    latest_state_path = _find_latest_state_file(outputs_dir)
    if latest_state_path is None:
        return []

    state = _load_state_json(latest_state_path)
    rows = [
        {
            "snapshot_timestamp": state["timestamp"],
            "spot_id": spot["id"],
            "status": spot["status"],
            "confidence": spot.get("confidence"),
            "created_at": state["timestamp"],
        }
        for spot in state["spots"]
    ]
    return rows[:limit]


def _load_state_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    data.setdefault("parking_lot_id", None)
    data.setdefault("occupancy_rate", _calculate_occupancy_rate(data))
    return data


def _calculate_occupancy_rate(state: dict[str, Any]) -> float:
    total_spots = state.get("total_spots", 0)
    if total_spots == 0:
        return 0.0

    return state.get("occupied_count", 0) / total_spots


def _history_row_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": state["timestamp"],
        "total_spots": state["total_spots"],
        "occupied_count": state["occupied_count"],
        "free_count": state["free_count"],
        "uncertain_count": state["uncertain_count"],
        "occupancy_rate": state["occupancy_rate"],
    }


def _find_latest_state_file(outputs_dir: Path) -> Path | None:
    return _find_latest_file(outputs_dir, "*_state.json")


def _find_latest_annotated_image(outputs_dir: Path) -> Path | None:
    return _find_latest_file(outputs_dir, "*_annotated.jpg")


def _find_latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None

    files = list(directory.glob(pattern))
    if not files:
        return None

    return max(files, key=lambda item: item.stat().st_mtime)
