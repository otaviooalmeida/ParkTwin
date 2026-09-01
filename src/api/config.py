import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ApiSettings:
    db_path: Path
    outputs_dir: Path
    uploads_dir: Path
    spots_path: Path
    base_image_path: Path
    model_path: Path
    imgsz: int
    occupancy_threshold: float
    parking_lot_id: str
    cors_origins: list[str]
    max_upload_bytes: int
    uncertain_overlap_threshold: float = 0.05
    change_confirmation_frames: int = 2
    retention_snapshots: int = 10000

    def __post_init__(self) -> None:
        if self.imgsz <= 0:
            raise ValueError("PARKTWIN_IMGSZ must be positive.")
        if not 0.0 <= self.occupancy_threshold <= 1.0:
            raise ValueError("PARKTWIN_OCCUPANCY_THRESHOLD must be between 0 and 1.")
        if self.max_upload_bytes <= 0:
            raise ValueError("PARKTWIN_MAX_UPLOAD_BYTES must be positive.")
        if not 0.0 <= self.uncertain_overlap_threshold <= self.occupancy_threshold:
            raise ValueError(
                "PARKTWIN_UNCERTAIN_OVERLAP_THRESHOLD must be between 0 and "
                "PARKTWIN_OCCUPANCY_THRESHOLD."
            )
        if self.change_confirmation_frames < 1:
            raise ValueError("PARKTWIN_CHANGE_CONFIRMATION_FRAMES must be at least 1.")
        if self.retention_snapshots < 1:
            raise ValueError("PARKTWIN_RETENTION_SNAPSHOTS must be at least 1.")


def get_settings() -> ApiSettings:
    uploads_dir = Path(os.getenv("PARKTWIN_UPLOADS_DIR", PROJECT_ROOT / "data" / "uploads"))
    spots_path = Path(
        os.getenv(
            "PARKTWIN_SPOTS_PATH",
            PROJECT_ROOT / "data" / "samples" / "spots_annotated.json",
        )
    )
    return ApiSettings(
        db_path=Path(os.getenv("PARKTWIN_DB_PATH", PROJECT_ROOT / "data" / "parktwin.db")),
        outputs_dir=Path(os.getenv("PARKTWIN_OUTPUTS_DIR", PROJECT_ROOT / "data" / "outputs")),
        uploads_dir=uploads_dir,
        spots_path=spots_path,
        base_image_path=Path(os.getenv("PARKTWIN_BASE_IMAGE_PATH", uploads_dir / "base_image.jpg")),
        model_path=Path(os.getenv("PARKTWIN_MODEL_PATH", "yolo11s.pt")),
        imgsz=int(os.getenv("PARKTWIN_IMGSZ", "1280")),
        occupancy_threshold=float(os.getenv("PARKTWIN_OCCUPANCY_THRESHOLD", "0.1")),
        parking_lot_id=os.getenv("PARKTWIN_PARKING_LOT_ID", "default"),
        cors_origins=_parse_cors_origins(
            os.getenv("PARKTWIN_CORS_ORIGINS", "http://localhost:5173")
        ),
        max_upload_bytes=int(os.getenv("PARKTWIN_MAX_UPLOAD_BYTES", str(15 * 1024 * 1024))),
        uncertain_overlap_threshold=float(
            os.getenv("PARKTWIN_UNCERTAIN_OVERLAP_THRESHOLD", "0.05")
        ),
        change_confirmation_frames=int(os.getenv("PARKTWIN_CHANGE_CONFIRMATION_FRAMES", "2")),
        retention_snapshots=int(os.getenv("PARKTWIN_RETENTION_SNAPSHOTS", "10000")),
    )


def _parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]
