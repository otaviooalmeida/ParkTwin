import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.config import get_settings
from api.schemas import (
    HealthResponse,
    OccupancyHistoryRow,
    ParkingLotConfigResponse,
    ParkingSpotConfig,
    ProcessImageResponse,
    SnapshotResponse,
    SpotEventResponse,
    UploadResponse,
)
from detection.yolo_detector import VehicleDetector
from parking.loader import load_parking_spots
from parking.occupancy import assign_occupancy
from parking.visualizer import save_annotated_image
from twin.repository import TwinRepository
from twin.state_manager import update_twin_state


settings = get_settings()

app = FastAPI(
    title="ParkTwin API",
    description="HTTP API for parking occupancy snapshots, events, setup, and imagery.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        database_exists=settings.db_path.exists(),
        latest_image_exists=_find_latest_annotated_image(settings.outputs_dir)
        is not None,
        base_image_exists=settings.base_image_path.exists(),
        spots_configured=settings.spots_path.exists(),
    )


@app.get("/api/config", response_model=ParkingLotConfigResponse)
def parking_lot_config() -> ParkingLotConfigResponse:
    return ParkingLotConfigResponse(
        base_image_exists=settings.base_image_path.exists(),
        base_image_url=(
            "/api/config/base-image" if settings.base_image_path.exists() else None
        ),
        spots=_load_spot_config(settings.spots_path),
    )


@app.post("/api/config/base-image", response_model=UploadResponse)
def upload_base_image(file: UploadFile = File(...)) -> UploadResponse:
    _ensure_image_upload(file)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    _save_upload(file, settings.base_image_path)
    return UploadResponse(
        filename=settings.base_image_path.name,
        url="/api/config/base-image",
    )


@app.get("/api/config/base-image")
def base_image() -> FileResponse:
    if not settings.base_image_path.exists():
        raise HTTPException(status_code=404, detail="No base image uploaded.")

    return FileResponse(settings.base_image_path, media_type="image/jpeg")


@app.get("/api/config/spots", response_model=list[ParkingSpotConfig])
def get_spots() -> list[ParkingSpotConfig]:
    return _load_spot_config(settings.spots_path)


@app.put("/api/config/spots", response_model=list[ParkingSpotConfig])
def save_spots(spots: list[ParkingSpotConfig]) -> list[ParkingSpotConfig]:
    if not spots:
        raise HTTPException(status_code=400, detail="At least one spot is required.")

    ids = [spot.id for spot in spots]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Spot IDs must be unique.")

    settings.spots_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.spots_path.open("w", encoding="utf-8") as file:
        json.dump([spot.dict() for spot in spots], file, indent=2)

    return spots


@app.post("/api/process-image", response_model=ProcessImageResponse)
def process_uploaded_image(file: UploadFile = File(...)) -> ProcessImageResponse:
    _ensure_image_upload(file)
    _ensure_processing_configured()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)

    upload_path = settings.uploads_dir / f"{uuid4().hex}_{_clean_filename(file.filename)}"
    annotated_path = settings.outputs_dir / "latest_annotated.jpg"
    _save_upload(file, upload_path)

    spots = load_parking_spots(settings.spots_path)
    detector = VehicleDetector(settings.model_path, imgsz=settings.imgsz)
    detections = detector.detect(upload_path)
    occupied_spots = assign_occupancy(
        spots,
        detections,
        overlap_threshold=settings.occupancy_threshold,
    )

    repository = TwinRepository(settings.db_path)
    previous_state = repository.get_latest_snapshot()
    state = update_twin_state(
        parking_lot_id=settings.parking_lot_id,
        current_spot_statuses=occupied_spots,
        previous_state=previous_state,
    )
    repository.save_snapshot(state)
    repository.save_spot_events(state)
    save_annotated_image(upload_path, occupied_spots, detections, annotated_path)

    return ProcessImageResponse(
        snapshot=SnapshotResponse(**asdict(state)),
        annotated_image_url="/api/images/latest",
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


def _ensure_processing_configured() -> None:
    if not settings.spots_path.exists():
        raise HTTPException(status_code=400, detail="No parking spots configured.")

    if not settings.model_path.exists():
        raise HTTPException(status_code=400, detail="YOLO model file not found.")


def _ensure_image_upload(file: UploadFile) -> None:
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload must be an image file.")


def _save_upload(file: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    file.file.close()


def _clean_filename(filename: str | None) -> str:
    if not filename:
        return "upload.jpg"

    return Path(filename).name.replace(" ", "_")


def _load_spot_config(path: Path) -> list[ParkingSpotConfig]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    return [ParkingSpotConfig(**item) for item in data]


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
