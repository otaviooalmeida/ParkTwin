from parking.geometry import bbox_center, point_in_polygon
from parking.models import ParkingSpot, VehicleDetection


def assign_occupancy(
    spots: list[ParkingSpot],
    detections: list[VehicleDetection],
) -> list[ParkingSpot]:
    occupied_spots: list[ParkingSpot] = []

    for spot in spots:
        best_detection = _find_best_detection_for_spot(spot, detections)

        if best_detection is None:
            occupied_spots.append(
                ParkingSpot(id=spot.id, polygon=spot.polygon, status="free")
            )
            continue

        occupied_spots.append(
            ParkingSpot(
                id=spot.id,
                polygon=spot.polygon,
                status="occupied",
                confidence=best_detection.confidence,
            )
        )

    return occupied_spots


def _find_best_detection_for_spot(
    spot: ParkingSpot,
    detections: list[VehicleDetection],
) -> VehicleDetection | None:
    matching_detections = [
        detection
        for detection in detections
        if point_in_polygon(bbox_center(detection.bbox), spot.polygon)
    ]

    if not matching_detections:
        return None

    return max(matching_detections, key=lambda detection: detection.confidence)
