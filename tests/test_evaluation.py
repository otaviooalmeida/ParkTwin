import pytest

from parktwin.evaluation import calculate_status_metrics


def test_calculate_status_metrics_builds_confusion_and_per_class_scores():
    metrics = calculate_status_metrics(
        {
            "A1": "free",
            "A2": "occupied",
            "A3": "uncertain",
            "A4": "occupied",
        },
        {
            "A1": "free",
            "A2": "free",
            "A3": "uncertain",
            "A4": "occupied",
        },
    )

    assert metrics["accuracy"] == 0.75
    assert metrics["confusion_matrix"]["occupied"]["free"] == 1
    assert metrics["per_status"]["occupied"]["precision"] == 1.0
    assert metrics["per_status"]["occupied"]["recall"] == 0.5
    assert metrics["per_status"]["uncertain"]["f1"] == 1.0


def test_calculate_status_metrics_allows_predictions_for_unlabeled_spots():
    metrics = calculate_status_metrics(
        {"A1": "free"},
        {"A1": "free", "A2": "occupied"},
    )

    assert metrics["labeled_spots"] == 1
    assert metrics["accuracy"] == 1.0


def test_calculate_status_metrics_rejects_missing_predictions():
    with pytest.raises(ValueError, match="A2"):
        calculate_status_metrics(
            {"A1": "free", "A2": "occupied"},
            {"A1": "free"},
        )


def test_calculate_status_metrics_rejects_empty_labels():
    with pytest.raises(ValueError, match="At least one"):
        calculate_status_metrics({}, {})
