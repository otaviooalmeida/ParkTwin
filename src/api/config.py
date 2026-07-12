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


def get_settings() -> ApiSettings:
    uploads_dir = Path(
        os.getenv("PARKTWIN_UPLOADS_DIR", PROJECT_ROOT / "data" / "uploads")
    )
    spots_path = Path(
        os.getenv(
            "PARKTWIN_SPOTS_PATH",
            PROJECT_ROOT / "data" / "samples" / "spots_annotated.json",
        )
    )
    return ApiSettings(
        db_path=Path(
            os.getenv("PARKTWIN_DB_PATH", PROJECT_ROOT / "data" / "parktwin.db")
        ),
        outputs_dir=Path(
            os.getenv("PARKTWIN_OUTPUTS_DIR", PROJECT_ROOT / "data" / "outputs")
        ),
        uploads_dir=uploads_dir,
        spots_path=spots_path,
        base_image_path=Path(
            os.getenv("PARKTWIN_BASE_IMAGE_PATH", uploads_dir / "base_image.jpg")
        ),
        model_path=Path(os.getenv("PARKTWIN_MODEL_PATH", "yolo11s.pt")),
        imgsz=int(os.getenv("PARKTWIN_IMGSZ", "1280")),
        occupancy_threshold=float(os.getenv("PARKTWIN_OCCUPANCY_THRESHOLD", "0.1")),
        parking_lot_id=os.getenv("PARKTWIN_PARKING_LOT_ID", "default"),
        cors_origins=_parse_cors_origins(
            os.getenv("PARKTWIN_CORS_ORIGINS", "http://localhost:5173")
        ),
    )


def _parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]
