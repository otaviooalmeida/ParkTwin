from parking.geometry import (
    bbox_area,
    bbox_center,
    bbox_intersects_polygon,
    bbox_polygon_overlap_ratio,
    point_in_polygon,
)


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


def test_bbox_intersects_polygon_returns_true_when_bbox_corner_is_inside():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_intersects_polygon([90, 90, 120, 120], polygon) is True


def test_bbox_intersects_polygon_returns_true_when_polygon_corner_is_inside_bbox():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_intersects_polygon([-10, -10, 10, 10], polygon) is True


def test_bbox_intersects_polygon_returns_true_when_edges_cross():
    polygon = [[40, 40], [60, 40], [60, 60], [40, 60]]

    assert bbox_intersects_polygon([30, 50, 70, 55], polygon) is True


def test_bbox_intersects_polygon_returns_false_without_overlap():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_intersects_polygon([120, 120, 140, 140], polygon) is False


def test_bbox_polygon_overlap_ratio_returns_intersection_area_over_bbox_area():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_polygon_overlap_ratio([50, 50, 150, 150], polygon) == 0.25


def test_bbox_polygon_overlap_ratio_returns_zero_without_overlap():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_polygon_overlap_ratio([120, 120, 140, 140], polygon) == 0


def test_bbox_polygon_overlap_ratio_handles_full_overlap():
    polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]

    assert bbox_polygon_overlap_ratio([10, 10, 40, 40], polygon) == 1
