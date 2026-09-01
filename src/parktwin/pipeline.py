"""Reusable orchestration for ParkTwin image processing."""

import logging
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from parking.loader import load_parking_spots
from parking.models import ParkingSpot, VehicleDetection
from parking.occupancy import assign_occupancy
from parking.visualizer import save_annotated_image
from twin.models import ParkingTwinState
from twin.repository import TwinRepository
from twin.state_manager import update_twin_state

logger = logging.getLogger(__name__)


class VehicleDetectorProtocol(Protocol):
    def detect(self, image_path: str | Path) -> list[VehicleDetection]: ...


@dataclass(frozen=True)
class ParkingAnalysis:
    spots: list[ParkingSpot]
    detections: list[VehicleDetection]


@dataclass(frozen=True)
class ProcessingResult:
    state: ParkingTwinState
    analysis: ParkingAnalysis
    annotated_image_path: Path
    processing_time_ms: float


def analyze_parking_image(
    image_path: str | Path,
    spots_path: str | Path,
    detector: VehicleDetectorProtocol,
    occupancy_threshold: float,
    uncertain_overlap_threshold: float | None = None,
) -> ParkingAnalysis:
    spots = load_parking_spots(spots_path)
    detections = detector.detect(image_path)
    uncertain_threshold = (
        min(0.05, occupancy_threshold)
        if uncertain_overlap_threshold is None
        else uncertain_overlap_threshold
    )
    occupied_spots = assign_occupancy(
        spots,
        detections,
        overlap_threshold=occupancy_threshold,
        uncertain_overlap_threshold=uncertain_threshold,
    )
    return ParkingAnalysis(spots=occupied_spots, detections=detections)


def process_parking_image(
    image_path: str | Path,
    spots_path: str | Path,
    detector: VehicleDetectorProtocol,
    repository: TwinRepository,
    parking_lot_id: str,
    annotated_image_path: str | Path,
    occupancy_threshold: float,
    *,
    draw_detections: bool = False,
    uncertain_overlap_threshold: float | None = None,
    change_confirmation_frames: int = 2,
    retention_snapshots: int = 10000,
) -> ProcessingResult:
    """Analyze one image and atomically publish its persisted state and rendered image."""
    started_at = perf_counter()
    analysis = analyze_parking_image(
        image_path=image_path,
        spots_path=spots_path,
        detector=detector,
        occupancy_threshold=occupancy_threshold,
        uncertain_overlap_threshold=uncertain_overlap_threshold,
    )
    previous_state = repository.get_latest_snapshot(parking_lot_id)
    state = update_twin_state(
        parking_lot_id=parking_lot_id,
        current_spot_statuses=analysis.spots,
        previous_state=previous_state,
        change_confirmation_frames=change_confirmation_frames,
    )

    output_path = Path(annotated_image_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(
        f".{output_path.stem}.{uuid4().hex}.tmp{output_path.suffix}"
    )

    try:
        save_annotated_image(
            image_path,
            analysis.spots,
            analysis.detections,
            temporary_path,
            draw_detections=draw_detections,
        )
        repository.save_state(
            state,
            previous_state,
            retention_snapshots=retention_snapshots,
        )
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    processing_time_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "processed parking image",
        extra={
            "parking_lot_id": parking_lot_id,
            "processing_time_ms": round(processing_time_ms, 2),
            "detection_count": len(analysis.detections),
            "occupied_count": state.occupied_count,
            "uncertain_count": state.uncertain_count,
        },
    )

    return ProcessingResult(
        state=state,
        analysis=analysis,
        annotated_image_path=output_path,
        processing_time_ms=processing_time_ms,
    )
