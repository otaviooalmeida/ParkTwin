# ParkTwin evaluation dataset

Each manifest case points to an image, its parking-space polygons and manually reviewed
spot statuses. Only cases with `"verified": true` are included by default.

Start from `manifest.example.json`, review every labeled spot against the source image,
and keep train/tuning images separate from the final evaluation set. Generated ParkTwin
state files must not be treated as ground truth.

Run an evaluation with:

```bash
python scripts/evaluate_parktwin.py evaluation/manifest.json \
  --model yolo11s.pt \
  --output evaluation/report.json
```

The report contains accuracy, macro F1, per-status precision/recall/F1 and a confusion
matrix. Reports are generated artifacts and should normally remain outside Git.
