
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

schema_path = (
    ROOT / "data" / "schemas" / "v1" /
    "tracking_frame.schema.json"
)

frames_path = (
    ROOT / "tests" / "data" / "fixtures" /
    "canonical_frames.json"
)

events_path = (
    ROOT / "tests" / "data" / "fixtures" /
    "canonical_events.json"
)


def test_tracking_frames():
    schema = json.loads(
        schema_path.read_text(encoding="utf-8-sig")
    )

    frames = json.loads(
        frames_path.read_text(encoding="utf-8")
    )

    events = json.loads(
        events_path.read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema)
    validator.check_schema(schema)

    assert len(frames) == 10800

    frame_ids = set()
    match_ids = {event["match_id"] for event in events}
    previous_tick = -1

    for index, frame in enumerate(frames):
        errors = list(validator.iter_errors(frame))

        assert not errors, (
            f"Frame {index}: {errors[0].message}"
            if errors else ""
        )

        assert frame["frame_id"] not in frame_ids
        frame_ids.add(frame["frame_id"])

        assert frame["match_id"] in match_ids
        assert frame["tick"] > previous_tick
        previous_tick = frame["tick"]

        # Check every stored position is on the pitch.
        positions = [
            frame["ball_position"],
            *frame["player_positions"].values()
        ]

        for x, y in positions:
            assert -1 <= x <= 106
            assert -1 <= y <= 69

    print(f"\nValidated {len(frames)} tracking frames")
    print("All frame IDs are unique")
    print("Events and frames share a match ID")
    print("Frames have increasing timestamps")
