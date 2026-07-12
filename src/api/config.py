import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ApiSettings:
    db_path: Path
    outputs_dir: Path
    cors_origins: list[str]


def get_settings() -> ApiSettings:
    return ApiSettings(
        db_path=Path(
            os.getenv("PARKTWIN_DB_PATH", PROJECT_ROOT / "data" / "parktwin.db")
        ),
        outputs_dir=Path(
            os.getenv("PARKTWIN_OUTPUTS_DIR", PROJECT_ROOT / "data" / "outputs")
        ),
        cors_origins=_parse_cors_origins(
            os.getenv("PARKTWIN_CORS_ORIGINS", "http://localhost:5173")
        ),
    )


def _parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]
