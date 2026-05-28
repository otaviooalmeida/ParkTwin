from parking.models import ParkingSpot, VehicleDetection
from parking.occupancy import assign_occupancy


def test_assign_occupancy_marks_spot_as_free_without_vehicle():
    spots = [ParkingSpot(id="A1", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])]

    result = assign_occupancy(spots, [])

    assert result[0].status == "free"
    assert result[0].confidence is None


def test_assign_occupancy_marks_spot_as_occupied_when_vehicle_center_is_inside():
    spots = [ParkingSpot(id="A1", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])]
    detections = [VehicleDetection(bbox=[40, 40, 60, 60], class_name="car", confidence=0.9)]

    result = assign_occupancy(spots, detections)

    assert result[0].status == "occupied"
    assert result[0].confidence == 0.9


def test_assign_occupancy_ignores_vehicle_outside_all_spots():
    spots = [ParkingSpot(id="A1", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])]
    detections = [
        VehicleDetection(bbox=[140, 140, 160, 160], class_name="car", confidence=0.9)
    ]

    result = assign_occupancy(spots, detections)

    assert result[0].status == "free"
    assert result[0].confidence is None


def test_assign_occupancy_keeps_highest_confidence_detection_for_same_spot():
    spots = [ParkingSpot(id="A1", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])]
    detections = [
        VehicleDetection(bbox=[10, 10, 20, 20], class_name="car", confidence=0.6),
        VehicleDetection(bbox=[40, 40, 60, 60], class_name="car", confidence=0.95),
    ]

    result = assign_occupancy(spots, detections)

    assert result[0].status == "occupied"
    assert result[0].confidence == 0.95
