import cv2
import numpy as np

from parking.models import ParkingSpot, VehicleDetection
from parking.visualizer import save_annotated_image


def test_save_annotated_image_writes_output_file(tmp_path):
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    spots = [
        ParkingSpot(
            id="A1",
            polygon=[[10, 10], [100, 10], [100, 100], [10, 100]],
            status="occupied",
            confidence=0.9,
        )
    ]
    detections = [VehicleDetection(bbox=[30, 30, 70, 70], class_name="car", confidence=0.9)]
    output_path = tmp_path / "annotated.jpg"

    result_path = save_annotated_image(image, spots, detections, output_path)

    assert result_path == output_path
    assert output_path.exists()
    assert cv2.imread(str(output_path)) is not None
