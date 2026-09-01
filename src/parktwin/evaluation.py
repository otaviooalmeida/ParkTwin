"""Classification metrics for parking-spot evaluation datasets."""

from typing import Any

from twin.models import SpotStatus

STATUSES: tuple[SpotStatus, ...] = ("free", "occupied", "uncertain")


def calculate_status_metrics(
    expected: dict[str, SpotStatus],
    predicted: dict[str, SpotStatus],
) -> dict[str, Any]:
    if not expected:
        raise ValueError("At least one labeled spot is required.")

    missing = sorted(set(expected) - set(predicted))
    if missing:
        raise ValueError(f"Predictions are missing labeled spots: {', '.join(missing)}")

    confusion = {
        expected_status: {predicted_status: 0 for predicted_status in STATUSES}
        for expected_status in STATUSES
    }
    correct = 0
    for spot_id, expected_status in expected.items():
        predicted_status = predicted[spot_id]
        confusion[expected_status][predicted_status] += 1
        correct += int(expected_status == predicted_status)

    per_status: dict[str, dict[str, float | int]] = {}
    for status in STATUSES:
        true_positive = confusion[status][status]
        false_positive = sum(confusion[other][status] for other in STATUSES if other != status)
        false_negative = sum(confusion[status][other] for other in STATUSES if other != status)
        precision = _safe_ratio(true_positive, true_positive + false_positive)
        recall = _safe_ratio(true_positive, true_positive + false_negative)
        f1_score = _safe_ratio(2 * precision * recall, precision + recall)
        per_status[status] = {
            "precision": precision,
            "recall": recall,
            "f1": f1_score,
            "support": sum(confusion[status].values()),
        }

    return {
        "labeled_spots": len(expected),
        "accuracy": correct / len(expected),
        "macro_f1": sum(float(per_status[status]["f1"]) for status in STATUSES) / len(STATUSES),
        "per_status": per_status,
        "confusion_matrix": confusion,
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
