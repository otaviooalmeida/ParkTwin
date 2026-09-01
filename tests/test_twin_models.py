from twin.models import SpotState, calculate_twin_counts


def test_calculate_twin_counts_counts_statuses_and_occupancy_rate():
    spots = [
        SpotState(id="A1", polygon=[[0, 0], [10, 0], [10, 10]], status="free"),
        SpotState(id="A2", polygon=[[20, 0], [30, 0], [30, 10]], status="occupied"),
        SpotState(id="A3", polygon=[[40, 0], [50, 0], [50, 10]], status="occupied"),
        SpotState(id="A4", polygon=[[60, 0], [70, 0], [70, 10]], status="uncertain"),
    ]

    counts = calculate_twin_counts(spots)

    assert counts == {
        "total_spots": 4,
        "occupied_count": 2,
        "free_count": 1,
        "uncertain_count": 1,
        "occupancy_rate": 0.5,
    }


def test_calculate_twin_counts_handles_empty_spots():
    counts = calculate_twin_counts([])

    assert counts == {
        "total_spots": 0,
        "occupied_count": 0,
        "free_count": 0,
        "uncertain_count": 0,
        "occupancy_rate": 0.0,
    }
