import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ParkTwin spot annotator</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #1f2328;
      color: #f6f8fa;
      display: grid;
      grid-template-columns: 1fr 280px;
      height: 100vh;
    }
    main {
      overflow: auto;
      padding: 16px;
    }
    aside {
      border-left: 1px solid #3d444d;
      padding: 16px;
      overflow: auto;
      background: #161b22;
    }
    canvas {
      max-width: 100%;
      height: auto;
      background: #000;
      cursor: crosshair;
    }
    button {
      width: 100%;
      margin: 4px 0;
      padding: 8px;
      border: 1px solid #3d444d;
      background: #30363d;
      color: #f6f8fa;
      cursor: pointer;
    }
    button:hover {
      background: #3d444d;
    }
    .spot {
      padding: 6px 8px;
      margin: 4px 0;
      border: 1px solid #3d444d;
      cursor: pointer;
    }
    .spot.selected {
      border-color: #f2cc60;
      background: #332b00;
    }
    .muted {
      color: #8b949e;
      font-size: 13px;
      line-height: 1.4;
    }
    .status {
      margin-top: 8px;
      color: #7ee787;
      min-height: 20px;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <main>
    <canvas id="canvas"></canvas>
  </main>
  <aside>
    <h2>ParkTwin</h2>
    <p class="muted">
      Left click: add point<br>
      Enter: finish spot<br>
      U: undo point<br>
      R: reset current polygon<br>
      Delete: delete selected spot<br>
      Right click inside spot: delete spot<br>
      Ctrl+S: save JSON
    </p>
    <button id="finish">Finish current spot</button>
    <button id="undo">Undo point</button>
    <button id="reset">Reset current</button>
    <button id="delete">Delete selected</button>
    <button id="save">Save JSON</button>
    <div class="status" id="status"></div>
    <h3>Spots</h3>
    <div id="spots"></div>
  </aside>
  <script>
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const spotsEl = document.getElementById("spots");
    const statusEl = document.getElementById("status");
    const image = new Image();

    let spots = [];
    let currentPolygon = [];
    let selectedSpotId = null;
    let reusableIds = [];
    let nextSpotNumber = 1;

    function setStatus(message) {
      statusEl.textContent = message;
    }

    function numericSuffix(id) {
      const match = id.match(/^(.*?)(\\d+)$/);
      return match ? Number(match[2]) : 0;
    }

    function updateNextSpotNumber() {
      nextSpotNumber = spots.reduce((highest, spot) => {
        return Math.max(highest, numericSuffix(spot.id));
      }, 0) + 1;
    }

    function nextSpotId() {
      if (reusableIds.length > 0) {
        return reusableIds.shift();
      }
      return "A" + nextSpotNumber++;
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      spots.forEach((spot) => drawPolygon(spot.polygon, spot.id, spot.id === selectedSpotId ? "#f2cc60" : "#2ea043"));
      drawPolygon(currentPolygon, "current", "#e3b341");
      renderSpotList();
    }

    function drawPolygon(polygon, label, color) {
      if (polygon.length === 0) {
        return;
      }

      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 3;

      ctx.beginPath();
      ctx.moveTo(polygon[0][0], polygon[0][1]);
      for (let i = 1; i < polygon.length; i++) {
        ctx.lineTo(polygon[i][0], polygon[i][1]);
      }
      if (polygon.length >= 3) {
        ctx.closePath();
      }
      ctx.stroke();

      polygon.forEach(([x, y]) => {
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.font = "18px Arial";
      ctx.lineWidth = 4;
      ctx.strokeStyle = "#000";
      ctx.strokeText(label, polygon[0][0], polygon[0][1] - 8);
      ctx.fillText(label, polygon[0][0], polygon[0][1] - 8);
    }

    function renderSpotList() {
      spotsEl.innerHTML = "";
      spots.forEach((spot) => {
        const item = document.createElement("div");
        item.className = "spot" + (spot.id === selectedSpotId ? " selected" : "");
        item.textContent = spot.id + " (" + spot.polygon.length + " pts)";
        item.onclick = () => {
          selectedSpotId = spot.id;
          draw();
        };
        spotsEl.appendChild(item);
      });
    }

    function canvasPoint(event) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return [
        Math.round((event.clientX - rect.left) * scaleX),
        Math.round((event.clientY - rect.top) * scaleY),
      ];
    }

    function pointInPolygon(point, polygon) {
      const [x, y] = point;
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i][0], yi = polygon[i][1];
        const xj = polygon[j][0], yj = polygon[j][1];
        const intersect = ((yi > y) !== (yj > y)) &&
          (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
        if (intersect) inside = !inside;
      }
      return inside;
    }

    function finishCurrentSpot() {
      if (currentPolygon.length < 3) {
        setStatus("A spot needs at least 3 points.");
        return;
      }
      const id = nextSpotId();
      spots.push({ id, polygon: currentPolygon });
      currentPolygon = [];
      selectedSpotId = id;
      setStatus("Spot added: " + id);
      draw();
    }

    function deleteSelectedSpot() {
      if (!selectedSpotId) {
        setStatus("No selected spot.");
        return;
      }
      const before = spots.length;
      spots = spots.filter((spot) => spot.id !== selectedSpotId);
      if (spots.length !== before) {
        reusableIds.push(selectedSpotId);
        reusableIds.sort((a, b) => numericSuffix(a) - numericSuffix(b));
        setStatus("Deleted spot: " + selectedSpotId);
        selectedSpotId = null;
        draw();
      }
    }

    async function saveSpots() {
      const response = await fetch("/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(spots),
      });
      if (!response.ok) {
        setStatus("Save failed.");
        return;
      }
      setStatus("JSON saved.");
    }

    canvas.addEventListener("click", (event) => {
      currentPolygon.push(canvasPoint(event));
      draw();
    });

    canvas.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      const point = canvasPoint(event);
      const spot = spots.find((candidate) => pointInPolygon(point, candidate.polygon));
      if (spot) {
        selectedSpotId = spot.id;
        deleteSelectedSpot();
      }
    });

    document.getElementById("finish").onclick = finishCurrentSpot;
    document.getElementById("undo").onclick = () => {
      currentPolygon.pop();
      draw();
    };
    document.getElementById("reset").onclick = () => {
      currentPolygon = [];
      draw();
    };
    document.getElementById("delete").onclick = deleteSelectedSpot;
    document.getElementById("save").onclick = saveSpots;

    document.addEventListener("keydown", (event) => {
      if (event.key === "Enter") finishCurrentSpot();
      if (event.key.toLowerCase() === "u") {
        currentPolygon.pop();
        draw();
      }
      if (event.key.toLowerCase() === "r") {
        currentPolygon = [];
        draw();
      }
      if (event.key === "Delete") deleteSelectedSpot();
      if (event.ctrlKey && event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveSpots();
      }
    });

    async function init() {
      const spotsResponse = await fetch("/spots");
      spots = await spotsResponse.json();
      updateNextSpotNumber();

      image.onload = () => {
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;
        draw();
      };
      image.src = "/image";
    }

    init();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Open a browser-based spot annotator.")
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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    image_path = Path(args.image_path).resolve()
    input_path = Path(args.input).resolve() if args.input else None
    output_path = Path(args.output).resolve()

    if not image_path.exists():
        raise FileNotFoundError(image_path)

    handler = _build_handler(image_path, input_path, output_path)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Open: http://{args.host}:{args.port}")
    print(f"Saving JSON to: {output_path}")
    server.serve_forever()


def _build_handler(image_path: Path, input_path: Path | None, output_path: Path):
    class AnnotatorHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = urlparse(self.path).path

            if route == "/":
                self._send_bytes(HTML_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif route == "/image":
                content_type = mimetypes.guess_type(image_path)[0] or "application/octet-stream"
                self._send_bytes(image_path.read_bytes(), content_type)
            elif route == "/spots":
                self._send_json(_load_spots(input_path or output_path))
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            route = urlparse(self.path).path

            if route != "/save":
                self.send_error(404)
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            spots = json.loads(body.decode("utf-8"))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as file:
                json.dump(spots, file, indent=2)

            self._send_json({"ok": True})

        def log_message(self, format: str, *args) -> None:
            return

        def _send_json(self, data) -> None:
            self._send_bytes(
                json.dumps(data).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _send_bytes(self, data: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return AnnotatorHandler


def _load_spots(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    spots = data["spots"] if isinstance(data, dict) and "spots" in data else data
    return [{"id": spot["id"], "polygon": spot["polygon"]} for spot in spots]


if __name__ == "__main__":
    main()
