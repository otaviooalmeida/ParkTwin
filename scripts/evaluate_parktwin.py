import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))

from detection.yolo_detector import VehicleDetector  # noqa: E402
from parktwin.evaluation import calculate_status_metrics  # noqa: E402
from parktwin.pipeline import analyze_parking_image  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate ParkTwin against a reviewed spot-status manifest."
    )
    parser.add_argument("manifest", help="Evaluation manifest JSON path.")
    parser.add_argument("--model", default="yolo11s.pt")
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--occupancy-threshold", type=float, default=0.1)
    parser.add_argument("--uncertain-threshold", type=float, default=0.05)
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument(
        "--include-unverified",
        action="store_true",
        help="Include cases not marked as verified. Intended only for bootstrapping.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = [
        case
        for case in manifest.get("cases", [])
        if case.get("verified") is True or args.include_unverified
    ]
    if not cases:
        raise ValueError("Manifest has no verified evaluation cases.")

    detector = VehicleDetector(args.model, imgsz=args.imgsz)
    expected_all = {}
    predicted_all = {}
    case_reports = []
    started_at = perf_counter()

    for case in cases:
        case_id = str(case["id"])
        image_path = _resolve_path(manifest_path, case["image"])
        spots_path = _resolve_path(manifest_path, case["spots"])
        analysis = analyze_parking_image(
            image_path,
            spots_path,
            detector,
            occupancy_threshold=args.occupancy_threshold,
            uncertain_overlap_threshold=args.uncertain_threshold,
        )
        predicted = {spot.id: spot.status for spot in analysis.spots}
        expected = case["expected"]
        metrics = calculate_status_metrics(expected, predicted)
        case_reports.append(
            {
                "id": case_id,
                "image": str(image_path),
                "detections": len(analysis.detections),
                "metrics": metrics,
            }
        )
        expected_all.update({f"{case_id}:{key}": value for key, value in expected.items()})
        predicted_all.update({f"{case_id}:{key}": predicted[key] for key in expected})

    report = {
        "model": args.model,
        "cases": case_reports,
        "aggregate": calculate_status_metrics(expected_all, predicted_all),
        "elapsed_seconds": perf_counter() - started_at,
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def _resolve_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else manifest_path.parent / path


if __name__ == "__main__":
    main()
