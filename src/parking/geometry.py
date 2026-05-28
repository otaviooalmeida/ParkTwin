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
