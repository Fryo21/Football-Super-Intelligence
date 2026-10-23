
import json

import pytest

from analytics.tracking_spatial_analysis import (
    spatial_sample,
    summarize_spatial_frames,
    enrich_tracking_message,
)


def frame(
    owner="RED_CM",
    red=(40, 20),
    blue=(42, 20),
):
    return {
        "match_id": "test_match",
        "frame_id": "frame_1",
        "match_second": 120.0,
        "player_positions": {
            "RED_CM": list(red),
            "BLU_CM": list(blue),
        },
        "ball_owner_id": owner,
    }


def test_nearby_opponent_and_zone():
    result = spatial_sample(
        frame(),
        radius=3,
    )

    assert result["ball_carrier_team"] == "RED"
    assert result["absolute_pitch_third"] == "middle"
    assert result["nearby_opponent_count"] == 1
    assert result["nearby_opponents"] == ["BLU_CM"]
    assert result["nearest_opponent_id"] == "BLU_CM"
    assert result["nearest_opponent_distance"] == 2.0


def test_distant_opponent_not_pressuring():
    result = spatial_sample(
        frame(blue=(60, 20))
    )

    assert result["pressure_present"] is False
    assert result["nearby_opponent_count"] == 0
    assert result["nearest_opponent_distance"] == 20.0


def test_no_owner_is_not_zero_pressure():
    result = spatial_sample(
        frame(owner=None)
    )

    assert result is None


def test_canonical_and_raw_aliases():
    src = frame()

    src["players"] = src.pop("player_positions")
    src["owner"] = src.pop("ball_owner_id")

    result = spatial_sample(src)

    assert result["nearby_opponent_count"] == 1


def test_summary_and_player_involvement():
    result = summarize_spatial_frames(
        [
            frame(),
            frame(blue=(60, 20)),
            frame(owner=None),
        ]
    )

    assert result["total_frames"] == 3
    assert result["frames_with_owner"] == 2

    assert result["zones"][0]["pressured_frames"] == 1
    assert result["zones"][0]["pressure_exposure_rate"] == 0.5

    assert result["defender_proximity_observations"] == {
        "BLU_CM": 1
    }


def test_unknown_owner_fails_loudly():
    with pytest.raises(ValueError, match="not found"):
        spatial_sample(
            frame(owner="RED_X")
        )


def test_tracking_message_enrichment():
    tracking_frame = {
        "match_id": "test_match",
        "frame_id": "frame_001",
        "match_second": 120.0,
        "ball_owner_id": "RED_CM",
        "player_positions": {
            "RED_CM": [40, 20],
            "BLU_CM": [42, 20],
            "BLU_ST": [70, 20],
        },
    }

    message = {
        "record_type": "frame",
        "payload_json": json.dumps(tracking_frame),
    }

    enriched = enrich_tracking_message(message)

    payload = json.loads(
        enriched["payload_json"]
    )

    assert enriched["record_type"] == "frame"
    assert payload["frame_id"] == "frame_001"
    assert payload["match_second"] == 120.0

    assert payload["player_positions"] == (
        tracking_frame["player_positions"]
    )

    spatial = payload["spatial_context"]

    assert spatial["owner_present"] is True
    assert spatial["ball_carrier_team"] == "RED"
    assert spatial["nearby_opponent_count"] == 1
    assert spatial["nearest_opponent_id"] == "BLU_CM"
    assert spatial["nearest_opponent_distance"] == 2.0
    assert spatial["pressure_present"] is True
    assert spatial["nearby_opponents"] == ["BLU_CM"]


def test_nearest_opponent_outside_pressure_radius():
    result = spatial_sample(
        frame(blue=(45, 20)),
        radius=3,
    )

    assert result["nearest_opponent_id"] == "BLU_CM"
    assert result["nearest_opponent_distance"] == 5.0
    assert result["nearby_opponent_count"] == 0
    assert result["pressure_present"] is False


def test_nearest_opponent_approach():
    before = spatial_sample(
        frame(blue=(45, 20))
    )

    after = spatial_sample(
        frame(blue=(41.5, 20))
    )

    assert before["nearest_opponent_distance"] == 5.0
    assert after["nearest_opponent_distance"] == 1.5

    assert before["pressure_present"] is False
    assert after["pressure_present"] is True
