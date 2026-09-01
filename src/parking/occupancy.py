from parking.geometry import bbox_polygon_overlap_ratio
from parking.models import ParkingSpot, VehicleDetection

DEFAULT_OCCUPANCY_OVERLAP_THRESHOLD = 0.3


def assign_occupancy(
    spots: list[ParkingSpot],
    detections: list[VehicleDetection],
    overlap_threshold: float = DEFAULT_OCCUPANCY_OVERLAP_THRESHOLD,
    uncertain_overlap_threshold: float | None = None,
) -> list[ParkingSpot]:
    """Assign each detection to at most one spot using overlap-first greedy matching."""
    uncertain_threshold = (
        overlap_threshold if uncertain_overlap_threshold is None else uncertain_overlap_threshold
    )
    _validate_thresholds(uncertain_threshold, overlap_threshold)

    candidates = sorted(
        (
            (
                bbox_polygon_overlap_ratio(detection.bbox, spot.polygon),
                detection.confidence,
                spot_index,
                detection_index,
            )
            for spot_index, spot in enumerate(spots)
            for detection_index, detection in enumerate(detections)
        ),
        reverse=True,
    )
    assignments: dict[int, tuple[VehicleDetection, float]] = {}
    assigned_detections: set[int] = set()

    for overlap, _confidence, spot_index, detection_index in candidates:
        if overlap < uncertain_threshold:
            break
        if spot_index in assignments or detection_index in assigned_detections:
            continue
        assignments[spot_index] = (detections[detection_index], overlap)
        assigned_detections.add(detection_index)

    return [
        _spot_from_assignment(
            spot,
            assignments.get(index),
            occupied_threshold=overlap_threshold,
        )
        for index, spot in enumerate(spots)
    ]


def _spot_from_assignment(
    spot: ParkingSpot,
    assignment: tuple[VehicleDetection, float] | None,
    *,
    occupied_threshold: float,
) -> ParkingSpot:
    if assignment is None:
        return ParkingSpot(id=spot.id, polygon=spot.polygon, status="free")

    detection, overlap = assignment
    return ParkingSpot(
        id=spot.id,
        polygon=spot.polygon,
        status="occupied" if overlap >= occupied_threshold else "uncertain",
        confidence=detection.confidence,
    )


def _validate_thresholds(uncertain_threshold: float, occupied_threshold: float) -> None:
    if not 0.0 <= uncertain_threshold <= occupied_threshold <= 1.0:
        raise ValueError("Overlap thresholds must satisfy 0 <= uncertain <= occupied <= 1.")
