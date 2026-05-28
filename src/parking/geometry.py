Point = list[float]
BBox = list[float]


# Calculates bounding box center
def bbox_center(bbox: BBox) -> Point:
    x1, y1, x2, y2 = bbox
    return [(x1 + x2) / 2, (y1 + y2) / 2]


# Calculates bouding box area
def bbox_area(bbox: BBox) -> float:
    x1, y1, x2, y2 = bbox
    return abs((x2 - x1) * (y2 - y1))


def bbox_intersects_polygon(bbox: BBox, polygon: list[Point]) -> bool:
    bbox_polygon = _bbox_to_polygon(bbox)

    if any(point_in_polygon(point, polygon) for point in bbox_polygon):
        return True

    if any(point_in_polygon(point, bbox_polygon) for point in polygon):
        return True

    return _polygons_have_intersecting_edges(bbox_polygon, polygon)


def bbox_polygon_overlap_ratio(bbox: BBox, polygon: list[Point]) -> float:
    area = bbox_area(bbox)
    if area == 0:
        return 0.0

    intersection_polygon = _clip_polygon(_bbox_to_polygon(bbox), polygon)
    if len(intersection_polygon) < 3:
        return 0.0

    return _polygon_area(intersection_polygon) / area


# Verifies if a given point is inside the polygon
def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    x, y = point
    inside = False
    vertex_count = len(polygon)

    for index in range(vertex_count):
        x1, y1 = polygon[index]
        x2, y2 = polygon[(index + 1) % vertex_count]

        if _point_on_segment(x, y, x1, y1, x2, y2):
            return True

        crosses_edge = (y1 > y) != (y2 > y)
        if crosses_edge:
            x_intersection = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < x_intersection:
                inside = not inside

    return inside


def _bbox_to_polygon(bbox: BBox) -> list[Point]:
    x1, y1, x2, y2 = bbox
    left = min(x1, x2)
    right = max(x1, x2)
    top = min(y1, y2)
    bottom = max(y1, y2)

    return [[left, top], [right, top], [right, bottom], [left, bottom]]


def _clip_polygon(subject_polygon: list[Point], clip_polygon: list[Point]) -> list[Point]:
    clipped_polygon = subject_polygon
    clip_is_counter_clockwise = _signed_polygon_area(clip_polygon) > 0

    for clip_start, clip_end in _polygon_edges(clip_polygon):
        input_polygon = clipped_polygon
        clipped_polygon = []

        if not input_polygon:
            break

        previous_point = input_polygon[-1]
        for current_point in input_polygon:
            current_inside = _is_inside_clip_edge(
                current_point,
                clip_start,
                clip_end,
                clip_is_counter_clockwise,
            )
            previous_inside = _is_inside_clip_edge(
                previous_point,
                clip_start,
                clip_end,
                clip_is_counter_clockwise,
            )

            if current_inside:
                if not previous_inside:
                    clipped_polygon.append(
                        _line_intersection(previous_point, current_point, clip_start, clip_end)
                    )
                clipped_polygon.append(current_point)
            elif previous_inside:
                clipped_polygon.append(
                    _line_intersection(previous_point, current_point, clip_start, clip_end)
                )

            previous_point = current_point

    return clipped_polygon


def _is_inside_clip_edge(
    point: Point,
    edge_start: Point,
    edge_end: Point,
    clip_is_counter_clockwise: bool,
) -> bool:
    x, y = point
    x1, y1 = edge_start
    x2, y2 = edge_end
    cross_product = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

    if clip_is_counter_clockwise:
        return cross_product >= -1e-9

    return cross_product <= 1e-9


def _line_intersection(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> Point:
    x1, y1 = first_start
    x2, y2 = first_end
    x3, y3 = second_start
    x4, y4 = second_end
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denominator) < 1e-9:
        return first_end

    x = (
        (x1 * y2 - y1 * x2) * (x3 - x4)
        - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / denominator
    y = (
        (x1 * y2 - y1 * x2) * (y3 - y4)
        - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / denominator

    return [x, y]


def _polygon_area(polygon: list[Point]) -> float:
    return abs(_signed_polygon_area(polygon))


def _signed_polygon_area(polygon: list[Point]) -> float:
    area = 0.0

    for start, end in _polygon_edges(polygon):
        area += start[0] * end[1] - end[0] * start[1]

    return area / 2


def _polygons_have_intersecting_edges(
    first_polygon: list[Point],
    second_polygon: list[Point],
) -> bool:
    for first_start, first_end in _polygon_edges(first_polygon):
        for second_start, second_end in _polygon_edges(second_polygon):
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return True

    return False


def _polygon_edges(polygon: list[Point]) -> list[tuple[Point, Point]]:
    return [
        (polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    ]


def _segments_intersect(
    first_start: Point,
    first_end: Point,
    second_start: Point,
    second_end: Point,
) -> bool:
    x1, y1 = first_start
    x2, y2 = first_end
    x3, y3 = second_start
    x4, y4 = second_end

    first_direction = _orientation(x1, y1, x2, y2, x3, y3)
    second_direction = _orientation(x1, y1, x2, y2, x4, y4)
    third_direction = _orientation(x3, y3, x4, y4, x1, y1)
    fourth_direction = _orientation(x3, y3, x4, y4, x2, y2)

    if first_direction != second_direction and third_direction != fourth_direction:
        return True

    if first_direction == 0 and _point_on_segment(x3, y3, x1, y1, x2, y2):
        return True
    if second_direction == 0 and _point_on_segment(x4, y4, x1, y1, x2, y2):
        return True
    if third_direction == 0 and _point_on_segment(x1, y1, x3, y3, x4, y4):
        return True
    if fourth_direction == 0 and _point_on_segment(x2, y2, x3, y3, x4, y4):
        return True

    return False


def _orientation(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
) -> int:
    value = (y2 - y1) * (x3 - x2) - (x2 - x1) * (y3 - y2)

    if abs(value) < 1e-9:
        return 0

    return 1 if value > 0 else 2


# Verifies if a given point is located in the border of the bbox
def _point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    cross_product = (y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)
    if abs(cross_product) > 1e-9:
        return False

    return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
