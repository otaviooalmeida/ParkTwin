import argparse
import json
from pathlib import Path

import cv2
import numpy as np


WINDOW_NAME = "ParkTwin spot annotator"


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate parking spot polygons.")
    parser.add_argument("image_path", help="Path to the parking lot image.")
    parser.add_argument(
        "--input",
        default=None,
        help="Existing spots JSON or twin state JSON to edit.",
    )
    parser.add_argument(
        "--output",
        default="data/samples/spots_annotated.json",
        help="Output JSON path. Default: data/samples/spots_annotated.json",
    )
    parser.add_argument(
        "--prefix",
        default="A",
        help="Parking spot ID prefix. Default: A",
    )
    args = parser.parse_args()

    image_path = Path(args.image_path)
    output_path = Path(args.output)
    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    input_path = Path(args.input) if args.input else None
    annotator = SpotAnnotator(
        image=image,
        output_path=output_path,
        prefix=args.prefix,
        input_path=input_path,
    )
    annotator.run()


class SpotAnnotator:
    def __init__(
        self,
        image,
        output_path: Path,
        prefix: str,
        input_path: Path | None = None,
    ) -> None:
        self.image = image
        self.output_path = output_path
        self.prefix = prefix
        self.spots: list[dict] = self._load_spots(input_path)
        self.current_polygon: list[list[int]] = []
        self.reusable_ids: list[str] = []
        self.next_spot_number = self._get_next_spot_number()

    def run(self) -> None:
        cv2.namedWindow(WINDOW_NAME)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

        while True:
            frame = self._render()
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(20) & 0xFF

            if key in (13, 10):
                self._finish_current_spot()
            elif key == ord("u"):
                self._undo_last_point()
            elif key == ord("r"):
                self._reset_current_polygon()
            elif key == ord("s"):
                self._save()
            elif key == ord("q") or key == 27:
                break

        cv2.destroyAllWindows()

    def _on_mouse(self, event, x: int, y: int, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_polygon.append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN:
            self._delete_spot_at_point(x, y)

    def _finish_current_spot(self) -> None:
        if len(self.current_polygon) < 3:
            print("A vaga precisa ter pelo menos 3 pontos.")
            return

        spot_id = self._next_spot_id()
        self.spots.append({"id": spot_id, "polygon": self.current_polygon.copy()})
        self.current_polygon.clear()
        print(f"Vaga salva na memoria: {spot_id}")

    def _undo_last_point(self) -> None:
        if self.current_polygon:
            self.current_polygon.pop()

    def _reset_current_polygon(self) -> None:
        self.current_polygon.clear()

    def _save(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as file:
            json.dump(self.spots, file, indent=2)
        print(f"Arquivo salvo: {self.output_path}")

    def _load_spots(self, input_path: Path | None) -> list[dict]:
        path = input_path or self.output_path
        if not path.exists():
            return []

        with path.open(encoding="utf-8") as file:
            data = json.load(file)

        spots = data["spots"] if isinstance(data, dict) and "spots" in data else data
        loaded_spots = [
            {"id": spot["id"], "polygon": spot["polygon"]}
            for spot in spots
        ]
        print(f"Anotacoes carregadas: {path} ({len(loaded_spots)} vagas)")
        return loaded_spots

    def _get_next_spot_number(self) -> int:
        highest_number = 0

        for spot in self.spots:
            spot_id = spot["id"]
            if not spot_id.startswith(self.prefix):
                continue

            suffix = spot_id[len(self.prefix) :]
            if suffix.isdigit():
                highest_number = max(highest_number, int(suffix))

        return highest_number + 1

    def _next_spot_id(self) -> str:
        if self.reusable_ids:
            return self.reusable_ids.pop(0)

        spot_id = f"{self.prefix}{self.next_spot_number}"
        self.next_spot_number += 1
        return spot_id

    def _delete_spot_at_point(self, x: int, y: int) -> None:
        for index, spot in enumerate(self.spots):
            polygon = np.array(spot["polygon"], dtype=np.int32)
            if cv2.pointPolygonTest(polygon, (x, y), False) >= 0:
                deleted_spot = self.spots.pop(index)
                self.reusable_ids.append(deleted_spot["id"])
                print(f"Vaga removida: {deleted_spot['id']}")
                return

    def _render(self):
        frame = self.image.copy()

        for spot in self.spots:
            self._draw_polygon(frame, spot["polygon"], (0, 180, 0), spot["id"])

        self._draw_polygon(frame, self.current_polygon, (0, 180, 220), "current")
        self._draw_help(frame)

        return frame

    def _draw_polygon(self, frame, polygon: list[list[int]], color, label: str) -> None:
        if not polygon:
            return

        for point in polygon:
            cv2.circle(frame, tuple(point), 4, color, -1)

        for index in range(len(polygon) - 1):
            cv2.line(frame, tuple(polygon[index]), tuple(polygon[index + 1]), color, 2)

        if len(polygon) >= 3:
            cv2.line(frame, tuple(polygon[-1]), tuple(polygon[0]), color, 2)

        cv2.putText(
            frame,
            label,
            tuple(polygon[0]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    def _draw_help(self, frame) -> None:
        lines = [
            "Click: add point",
            "Right click spot: delete spot",
            "Enter: finish spot",
            "U: undo point | R: reset current",
            "S: save JSON | Q/Esc: quit",
        ]

        y = 24
        for line in lines:
            cv2.putText(
                frame,
                line,
                (10, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            y += 24


if __name__ == "__main__":
    main()
