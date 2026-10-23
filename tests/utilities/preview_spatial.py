"""Save to scripts/preview_spatial.py; run from repository root with -m."""
import json
from pathlib import Path
from analytics.tracking_spatial_analysis import summarize_spatial_frames

root = Path(__file__).resolve().parents[1]
frames_path = root / "tests" / "data" / "fixtures" / "canonical_frames.json"
frames = json.loads(frames_path.read_text(encoding="utf-8"))
report = summarize_spatial_frames(frames)
print(json.dumps(report, indent=2))
