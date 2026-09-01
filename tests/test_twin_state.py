import json
from datetime import datetime

from parking.models import ParkingSpot
from twin.models import ParkingTwinState, SpotState
from twin.state import TwinState, build_twin_state, save_twin_state


def test_build_twin_state_counts_spots_by_status():
    spots = [
        ParkingSpot(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        ParkingSpot(
            id="A2",
            polygon=[[20, 0], [30, 0], [30, 10]],
            status="occupied",
            confidence=0.9,
        ),
        ParkingSpot(id="A3", polygon=[[40, 0], [50, 0], [50, 10]], status="uncertain"),
    ]

    state = build_twin_state(spots)

    assert isinstance(state, TwinState)
    assert isinstance(state, ParkingTwinState)
    assert datetime.fromisoformat(state.timestamp)
    assert state.spots == [
        SpotState(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        SpotState(
            id="A2",
            polygon=[[20, 0], [30, 0], [30, 10]],
            status="occupied",
            confidence=0.9,
        ),
        SpotState(id="A3", polygon=[[40, 0], [50, 0], [50, 10]], status="uncertain"),
    ]
    assert state.total_spots == 3
    assert state.free_count == 1
    assert state.occupied_count == 1
    assert state.uncertain_count == 1
    assert state.occupancy_rate == 1 / 3


def test_save_twin_state_writes_json(tmp_path):
    spots = [
        ParkingSpot(
            id="A1",
            polygon=[[0, 0], [10, 0], [10, 10]],
            status="occupied",
            confidence=0.85,
        )
    ]
    state = build_twin_state(spots)
    output_path = tmp_path / "nested" / "state.json"

    save_twin_state(state, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["timestamp"] == state.timestamp
    assert data["total_spots"] == 1
    assert data["occupied_count"] == 1
    assert data["free_count"] == 0
    assert data["uncertain_count"] == 0
    assert data["occupancy_rate"] == 1.0
    assert data["spots"] == [
        {
            "id": "A1",
            "polygon": [[0, 0], [10, 0], [10, 10]],
            "status": "occupied",
            "confidence": 0.85,
            "occupied_since": None,
            "last_changed_at": None,
            "pending_status": None,
            "pending_count": 0,
        }
    ]
