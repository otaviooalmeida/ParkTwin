import pytest

from parking.models import ParkingSpot, VehicleDetection
from parking.occupancy import assign_occupancy


def test_assign_occupancy_does_not_use_one_detection_for_multiple_spots():
    spots = [
        ParkingSpot(id="A1", polygon=[[0, 0], [60, 0], [60, 100], [0, 100]]),
        ParkingSpot(id="A2", polygon=[[40, 0], [100, 0], [100, 100], [40, 100]]),
    ]
    detection = VehicleDetection(
        bbox=[30, 20, 70, 80],
        class_name="car",
        confidence=0.9,
    )

    result = assign_occupancy(spots, [detection], overlap_threshold=0.2)

    assert [spot.status for spot in result].count("occupied") == 1
    assert [spot.status for spot in result].count("free") == 1


def test_assign_occupancy_marks_borderline_overlap_as_uncertain():
    spot = ParkingSpot(
        id="A1",
        polygon=[[0, 0], [100, 0], [100, 100], [0, 100]],
    )
    detection = VehicleDetection(
        bbox=[90, 90, 150, 150],
        class_name="car",
        confidence=0.8,
    )

    result = assign_occupancy(
        [spot],
        [detection],
        overlap_threshold=0.1,
        uncertain_overlap_threshold=0.02,
    )

    assert result[0].status == "uncertain"
    assert result[0].confidence == 0.8


@pytest.mark.parametrize(
    ("uncertain_threshold", "occupied_threshold"),
    [(-0.1, 0.1), (0.2, 0.1), (0.1, 1.1)],
)
def test_assign_occupancy_rejects_invalid_thresholds(
    uncertain_threshold,
    occupied_threshold,
):
    with pytest.raises(ValueError, match="0 <= uncertain <= occupied <= 1"):
        assign_occupancy(
            [],
            [],
            overlap_threshold=occupied_threshold,
            uncertain_overlap_threshold=uncertain_threshold,
        )
