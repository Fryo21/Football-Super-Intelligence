
"""Calculate spatial intelligence from canonical football tracking frames.

Provides ball-carrier positioning, opponent proximity, pressure
indicators, offline summaries, and streaming message enrichment.

Distances use source coordinate units, not verified metres.
"""

from __future__ import annotations

import json
from collections import defaultdict
from math import hypot, isfinite
from typing import Any, Iterable

from analytics.match_config import MatchConfig


# Default settings preserve the existing spatial calculations.
DEFAULT_CONFIG = MatchConfig()

PITCH_LENGTH = DEFAULT_CONFIG.pitch_length
PITCH_WIDTH = DEFAULT_CONFIG.pitch_width
PRESSURE_RADIUS = DEFAULT_CONFIG.pressure_radius

SPATIAL_VERSION = "1.0.0"


# ---------------------------------------------------------
# Coordinate and data helpers
# ---------------------------------------------------------

def _xy(value: Any) -> tuple[float, float]:
    """Extract and validate X/Y coordinates."""

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        x, y = float(value[0]), float(value[1])

    elif isinstance(value, dict):
        x = float(value["x"])
        y = float(value["y"])

    else:
        raise ValueError(
            f"Expected [x,y] or {{x,y}}, got {type(value).__name__}"
        )

    if not (isfinite(x) and isfinite(y)):
        raise ValueError("Non-finite coordinate")

    return x, y


def _team_id(player_id: str) -> str:
    """Extract a Footysim team prefix from a player ID."""

    if "_" not in player_id:
        raise ValueError(
            f"Cannot infer Footysim team from player ID: {player_id}"
        )

    return player_id.split("_", 1)[0]


def _payload(frame: dict) -> dict:
    """Read a canonical frame or streaming payload."""

    if "payload_json" not in frame:
        return frame

    payload = frame["payload_json"]

    if isinstance(payload, str):
        return json.loads(payload)

    if isinstance(payload, dict):
        return payload

    raise ValueError("Invalid payload_json")


def _settings(
    radius: float,
    pitch_length: float,
    config: MatchConfig | None,
) -> tuple[float, float]:
    """Resolve and validate spatial analysis settings."""

    if config is not None:
        radius = config.pressure_radius
        pitch_length = config.pitch_length

    if not (isfinite(radius) and isfinite(pitch_length)):
        raise ValueError(
            "Radius and pitch length must be finite"
        )

    if radius <= 0 or pitch_length <= 0:
        raise ValueError(
            "Radius and pitch length must be positive"
        )

    return radius, pitch_length


# ---------------------------------------------------------
# Spatial calculations
# ---------------------------------------------------------

def spatial_sample(
    frame: dict,
    *,
    radius: float = PRESSURE_RADIUS,
    pitch_length: float = PITCH_LENGTH,
    config: MatchConfig | None = None,
) -> dict | None:
    """Calculate ball-carrier position and opponent proximity."""

    radius, pitch_length = _settings(
        radius,
        pitch_length,
        config,
    )

    frame = _payload(frame)

    players = frame.get(
        "player_positions",
        frame.get("players"),
    )

    if not isinstance(players, dict):
        raise ValueError(
            "Frame lacks dictionary player_positions/players"
        )

    owner = frame.get(
        "ball_owner_id",
        frame.get("ball_owner", frame.get("owner")),
    )

    # Frames without possession have no ball-carrier context.
    if not owner:
        return None

    if owner not in players:
        raise ValueError(
            f"Owner {owner} not found among player positions"
        )

    owner_x, owner_y = _xy(players[owner])
    owner_team = _team_id(str(owner))

    opponents = []

    for player_id, position in players.items():

        player_team = _team_id(str(player_id))

        if player_team == owner_team:
            continue

        player_x, player_y = _xy(position)

        distance = hypot(
            player_x - owner_x,
            player_y - owner_y,
        )

        opponents.append(
            (str(player_id), round(distance, 4))
        )

    # Nearest opponent first; player ID resolves distance ties.
    opponents.sort(
        key=lambda item: (item[1], item[0])
    )

    nearby_opponents = [
        (player_id, distance)
        for player_id, distance in opponents
        if distance <= radius
    ]

    # Absolute X-axis thirds, independent of attack direction.
    zone_index = min(
        2,
        max(
            0,
            int(owner_x / (pitch_length / 3.0)),
        ),
    )

    return {
        "match_id": frame.get("match_id"),
        "frame_id": frame.get("frame_id"),
        "match_second": frame.get(
            "match_second",
            frame.get("t"),
        ),

        "ball_carrier_id": str(owner),
        "ball_carrier_team": owner_team,

        "absolute_pitch_third": (
            "left",
            "middle",
            "right",
        )[zone_index],

        "nearest_opponent_id": (
            opponents[0][0] if opponents else None
        ),

        "nearest_opponent_distance": (
            opponents[0][1] if opponents else None
        ),

        "nearby_opponent_count": len(nearby_opponents),

        "pressure_present": bool(nearby_opponents),

        "nearby_opponents": [
            player_id
            for player_id, _ in nearby_opponents
        ],
    }


# ---------------------------------------------------------
# Offline spatial summaries
# ---------------------------------------------------------

def summarize_spatial_frames(
    frames: Iterable[dict],
    *,
    radius: float = PRESSURE_RADIUS,
    config: MatchConfig | None = None,
) -> dict:
    """Aggregate spatial observations for offline validation."""

    radius, pitch_length = _settings(
        radius,
        PITCH_LENGTH,
        config,
    )

    by_zone = defaultdict(
        lambda: {
            "owned_frames": 0,
            "pressured_frames": 0,
            "nearby_defender_observations": 0,
        }
    )

    defender_counts = defaultdict(int)

    frame_count = 0
    owned_count = 0

    for frame in frames:
        frame_count += 1

        sample = spatial_sample(
            frame,
            radius=radius,
            pitch_length=pitch_length,
        )

        if sample is None:
            continue

        owned_count += 1

        key = (
            sample["ball_carrier_team"],
            sample["absolute_pitch_third"],
        )

        row = by_zone[key]

        row["owned_frames"] += 1

        row["pressured_frames"] += int(
            sample["pressure_present"]
        )

        row["nearby_defender_observations"] += (
            sample["nearby_opponent_count"]
        )

        for defender_id in sample["nearby_opponents"]:
            defender_counts[defender_id] += 1

    zones = []

    for (team, zone), row in sorted(by_zone.items()):

        owned_frames = row["owned_frames"]

        zones.append(
            {
                "ball_carrier_team": team,
                "absolute_pitch_third": zone,
                **row,
                "pressure_exposure_rate": round(
                    row["pressured_frames"] / owned_frames,
                    4,
                ),
            }
        )

    return {
        "total_frames": frame_count,
        "frames_with_owner": owned_count,
        "pressure_radius_coordinate_units": radius,
        "zones": zones,
        "defender_proximity_observations": dict(
            sorted(defender_counts.items())
        ),
    }


# ---------------------------------------------------------
# Streaming enrichment
# ---------------------------------------------------------

def enrich_tracking_message(
    message: dict,
    *,
    radius: float = PRESSURE_RADIUS,
    config: MatchConfig | None = None,
) -> dict:
    """Add spatial context to a tracking streaming message."""

    if message.get("record_type") != "frame":
        return message

    radius, pitch_length = _settings(
        radius,
        PITCH_LENGTH,
        config,
    )

    payload = message.get("payload_json")

    if isinstance(payload, str):
        payload = json.loads(payload)

    elif isinstance(payload, dict):
        payload = dict(payload)

    else:
        raise ValueError("Invalid tracking payload")

    sample = spatial_sample(
        payload,
        radius=radius,
        pitch_length=pitch_length,
    )

    spatial_context = {
        "version": SPATIAL_VERSION,
        "radius_coordinate_units": radius,
        "owner_present": sample is not None,

        "ball_carrier_id": (
            sample["ball_carrier_id"]
            if sample else None
        ),

        "ball_carrier_team": (
            sample["ball_carrier_team"]
            if sample else None
        ),

        "absolute_pitch_third": (
            sample["absolute_pitch_third"]
            if sample else None
        ),

        "nearest_opponent_id": (
            sample["nearest_opponent_id"]
            if sample else None
        ),

        "nearest_opponent_distance": (
            sample["nearest_opponent_distance"]
            if sample else None
        ),

        "nearby_opponent_count": (
            sample["nearby_opponent_count"]
            if sample else None
        ),

        "pressure_present": (
            sample["pressure_present"]
            if sample else None
        ),

        "nearby_opponents": (
            sample["nearby_opponents"]
            if sample else []
        ),
    }

    # Preserve canonical tracking fields and envelope structure.
    payload["spatial_context"] = spatial_context

    enriched_message = dict(message)

    enriched_message["payload_json"] = json.dumps(
        payload,
        separators=(",", ":"),
        allow_nan=False,
    )

    return enriched_message
