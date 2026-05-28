from parking.geometry import bbox_area, bbox_center, point_in_polygon


def test_bbox_center_returns_center_point():
    assert bbox_center([10, 20, 30, 60]) == [20, 40]


def test_bbox_area_returns_width_times_height():
    assert bbox_area([10, 20, 30, 60]) == 800


def test_bbox_area_handles_inverted_coordinates():
    assert bbox_area([30, 60, 10, 20]) == 800


def test_point_in_polygon_returns_true_for_inside_point():
    polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]

    assert point_in_polygon([5, 5], polygon) is True


def test_point_in_polygon_returns_false_for_outside_point():
    polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]

    assert point_in_polygon([15, 5], polygon) is False


def test_point_in_polygon_treats_boundary_as_inside():
    polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]

    assert point_in_polygon([10, 5], polygon) is True


def test_point_in_polygon_works_with_triangle():
    polygon = [[0, 0], [10, 0], [5, 10]]

    assert point_in_polygon([5, 5], polygon) is True
    assert point_in_polygon([9, 9], polygon) is False
