import json
from dataclasses import replace

import cv2
import numpy as np
from fastapi.testclient import TestClient

import api.app as app_module
from api.config import ApiSettings
from parking.models import VehicleDetection
from twin.models import ParkingTwinState, SpotState
from twin.repository import TwinRepository


class StubDetector:
    def detect(self, image_path):
        return [
            VehicleDetection(
                bbox=[5, 5, 25, 25],
                class_name="car",
                confidence=0.95,
            )
        ]


def test_process_image_uses_pipeline_and_removes_transient_upload(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    settings.model_path.touch()
    settings.spots_path.parent.mkdir(parents=True)
    settings.spots_path.write_text(
        json.dumps(
            [
                {
                    "id": "A1",
                    "polygon": [[0, 0], [30, 0], [30, 30], [0, 30]],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "settings", settings)
    monkeypatch.setattr(app_module, "_get_detector", lambda: StubDetector())
    client = TestClient(app_module.app)

    response = client.post(
        "/api/process-image",
        files={"file": ("frame.png", _image_bytes(".png"), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["snapshot"]["occupied_count"] == 1
    assert settings.db_path.exists()
    assert (settings.outputs_dir / "latest_annotated.jpg").exists()
    assert list(settings.uploads_dir.iterdir()) == []


def test_upload_rejects_spoofed_image_content(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "settings", _settings(tmp_path))
    client = TestClient(app_module.app)

    response = client.post(
        "/api/config/base-image",
        files={"file": ("fake.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded content is not a valid image."


def test_upload_enforces_configured_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "settings",
        replace(_settings(tmp_path), max_upload_bytes=4),
    )
    client = TestClient(app_module.app)

    response = client.post(
        "/api/config/base-image",
        files={"file": ("frame.jpg", _image_bytes(".jpg"), "image/jpeg")},
    )

    assert response.status_code == 413


def test_detector_is_created_only_once(tmp_path, monkeypatch):
    created = []
    settings = _settings(tmp_path)

    class DetectorFactory:
        def __init__(self, model_path, imgsz):
            created.append((model_path, imgsz))

    monkeypatch.setattr(app_module, "settings", settings)
    monkeypatch.setattr(app_module, "VehicleDetector", DetectorFactory)
    monkeypatch.setattr(app_module, "_detector", None)

    assert app_module._get_detector() is app_module._get_detector()
    assert created == [(settings.model_path, settings.imgsz)]


def test_health_exposes_operational_readiness(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    settings.model_path.touch()
    monkeypatch.setattr(app_module, "settings", settings)
    monkeypatch.setattr(app_module, "_detector", None)

    response = TestClient(app_module.app).get("/health")

    assert response.status_code == 200
    assert response.json()["model_exists"] is True
    assert response.json()["detector_loaded"] is False


def test_latest_snapshot_is_scoped_to_configured_parking_lot(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    repository = TwinRepository(settings.db_path)
    repository.save_snapshot(_state("2026-01-01T10:00:00+00:00", "test-lot", "free"))
    repository.save_snapshot(_state("2026-01-01T10:01:00+00:00", "other-lot", "occupied"))
    monkeypatch.setattr(app_module, "settings", settings)

    response = TestClient(app_module.app).get("/api/snapshots/latest")

    assert response.status_code == 200
    assert response.json()["parking_lot_id"] == "test-lot"
    assert response.json()["occupied_count"] == 0


def test_history_endpoint_supports_window_pagination(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    repository = TwinRepository(settings.db_path)
    for minute in range(3):
        repository.save_snapshot(_state(f"2026-01-01T10:0{minute}:00+00:00", "test-lot", "free"))
    monkeypatch.setattr(app_module, "settings", settings)

    response = TestClient(app_module.app).get("/api/history?limit=1&offset=1")

    assert response.status_code == 200
    assert [row["timestamp"] for row in response.json()] == ["2026-01-01T10:01:00+00:00"]


def test_existing_database_does_not_fall_back_to_global_state_files(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    TwinRepository(settings.db_path)
    settings.outputs_dir.mkdir()
    (settings.outputs_dir / "other_state.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-01-01T10:00:00+00:00",
                "parking_lot_id": "other-lot",
                "spots": [],
                "total_spots": 0,
                "occupied_count": 0,
                "free_count": 0,
                "uncertain_count": 0,
                "occupancy_rate": 0.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(app_module, "settings", settings)

    response = TestClient(app_module.app).get("/api/snapshots/latest")

    assert response.status_code == 404


def _state(timestamp, parking_lot_id, status):
    spot = SpotState(
        id="A1",
        polygon=[[0, 0], [10, 0], [10, 10]],
        status=status,
    )
    return ParkingTwinState(
        timestamp=timestamp,
        spots=[spot],
        total_spots=1,
        occupied_count=int(status == "occupied"),
        free_count=int(status == "free"),
        uncertain_count=int(status == "uncertain"),
        occupancy_rate=float(status == "occupied"),
        parking_lot_id=parking_lot_id,
    )


def _settings(tmp_path) -> ApiSettings:
    uploads_dir = tmp_path / "uploads"
    return ApiSettings(
        db_path=tmp_path / "parktwin.db",
        outputs_dir=tmp_path / "outputs",
        uploads_dir=uploads_dir,
        spots_path=tmp_path / "config" / "spots.json",
        base_image_path=uploads_dir / "base_image.jpg",
        model_path=tmp_path / "model.pt",
        imgsz=640,
        occupancy_threshold=0.1,
        parking_lot_id="test-lot",
        cors_origins=["http://localhost:5173"],
        max_upload_bytes=1024 * 1024,
    )


def _image_bytes(extension):
    ok, encoded = cv2.imencode(extension, np.zeros((32, 32, 3), dtype=np.uint8))
    assert ok
    return encoded.tobytes()
