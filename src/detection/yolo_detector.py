from pathlib import Path

from parking.models import VehicleDetection


VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}


class VehicleDetector:
    def __init__(self, model_path: str | Path, imgsz: int | None = None) -> None:
        from ultralytics import YOLO

        self.model = YOLO(str(model_path))
        self.imgsz = imgsz

    def detect(self, image_path: str | Path) -> list[VehicleDetection]:
        predict_kwargs = {}
        if self.imgsz is not None:
            predict_kwargs["imgsz"] = self.imgsz

        results = self.model(str(image_path), **predict_kwargs)
        detections: list[VehicleDetection] = []

        for result in results:
            names = result.names

            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = names[class_id]

                if class_name not in VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])

                detections.append(
                    VehicleDetection(
                        bbox=[float(x1), float(y1), float(x2), float(y2)],
                        class_name=class_name,
                        confidence=confidence,
                    )
                )

        return detections
