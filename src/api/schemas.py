from typing import Literal

from pydantic import BaseModel


SpotStatus = Literal["free", "occupied", "uncertain"]
Point = tuple[float, float]


class SpotStateResponse(BaseModel):
    id: str
    polygon: list[Point]
    status: SpotStatus
    confidence: float | None = None
    occupied_since: str | None = None
    last_changed_at: str | None = None


class SnapshotResponse(BaseModel):
    timestamp: str
    parking_lot_id: str | None = None
    spots: list[SpotStateResponse]
    total_spots: int
    occupied_count: int
    free_count: int
    uncertain_count: int
    occupancy_rate: float


class OccupancyHistoryRow(BaseModel):
    timestamp: str
    total_spots: int
    occupied_count: int
    free_count: int
    uncertain_count: int
    occupancy_rate: float


class SpotEventResponse(BaseModel):
    snapshot_timestamp: str
    spot_id: str
    status: SpotStatus
    confidence: float | None = None
    created_at: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database_exists: bool
    latest_image_exists: bool
