from parking.geometry import bbox_polygon_overlap_ratio
from parking.models import ParkingSpot, VehicleDetection


DEFAULT_OCCUPANCY_OVERLAP_THRESHOLD = 0.3


def assign_occupancy(
    spots: list[ParkingSpot],
    detections: list[VehicleDetection],
    overlap_threshold: float = DEFAULT_OCCUPANCY_OVERLAP_THRESHOLD,
) -> list[ParkingSpot]:
    occupied_spots: list[ParkingSpot] = []

    for spot in spots:
        best_detection = _find_best_detection_for_spot(
            spot,
            detections,
            overlap_threshold,
        )

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
    overlap_threshold: float,
) -> VehicleDetection | None:
    matching_detections = [
        detection
        for detection in detections
        if bbox_polygon_overlap_ratio(detection.bbox, spot.polygon) >= overlap_threshold
    ]

    if not matching_detections:
        return None

    return max(matching_detections, key=lambda detection: detection.confidence)
