
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "data" / "fixtures"
SCHEMAS = ROOT / "data" / "schemas" / "v1"


def test_match_metadata():
    schema = json.loads(
        (SCHEMAS / "match_metadata.schema.json")
        .read_text(encoding="utf-8-sig")
    )

    metadata = json.loads(
        (FIXTURES / "canonical_metadata.json")
        .read_text(encoding="utf-8")
    )

    events = json.loads(
        (FIXTURES / "canonical_events.json")
        .read_text(encoding="utf-8")
    )

    frames = json.loads(
        (FIXTURES / "canonical_frames.json")
        .read_text(encoding="utf-8")
    )

    validator = Draft202012Validator(schema)
    validator.check_schema(schema)
    validator.validate(metadata)

    match_id = metadata["match_id"]

    assert all(e["match_id"] == match_id for e in events)
    assert all(f["match_id"] == match_id for f in frames)

    team_ids = set(metadata["teams"])
    player_ids = set()

    for team in metadata["teams"].values():
        player_ids.update(p["pid"] for p in team["players"])

    assert len(player_ids) == 22

    for event in events:
        if event["team_id"] is not None:
            assert event["team_id"] in team_ids

        if event["player_id"] is not None:
            assert event["player_id"] in player_ids

    for frame in frames:
        assert set(frame["player_positions"]) == player_ids

        if frame["ball_owner_id"] is not None:
            assert frame["ball_owner_id"] in player_ids

    assert "final_score" not in metadata

    print("\nMatch metadata validated")
    print("Match IDs consistent")
    print("Teams and players verified")
    print("No final-score leakage")
