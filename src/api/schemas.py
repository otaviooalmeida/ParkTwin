from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

SpotStatus = Literal["free", "occupied", "uncertain"]
Point = tuple[FiniteFloat, FiniteFloat]


class ParkingSpotConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1)
    polygon: list[Point] = Field(min_length=3)


class SpotStateResponse(BaseModel):
    id: str
    polygon: list[Point]
    status: SpotStatus
    confidence: float | None = None
    occupied_since: str | None = None
    last_changed_at: str | None = None
    pending_status: SpotStatus | None = None
    pending_count: int = 0


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
    model_exists: bool
    detector_loaded: bool
    latest_image_exists: bool
    base_image_exists: bool
    spots_configured: bool


class ParkingLotConfigResponse(BaseModel):
    base_image_exists: bool
    base_image_url: str | None = None
    spots: list[ParkingSpotConfig]


class UploadResponse(BaseModel):
    filename: str
    url: str


class ProcessImageResponse(BaseModel):
    snapshot: SnapshotResponse
    annotated_image_url: str
    detection_count: int
    processing_time_ms: float
