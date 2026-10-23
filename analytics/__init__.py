
"""Deterministic spatial intelligence for Footysim tracking frames.

Calculates:
- Ball-carrier position and pitch zone
- Nearest opposing player and distance
- Nearby defenders within a configurable pressure radius
- Defensive proximity and pressure exposure
- Spatial enrichment for the existing Fabric streaming publisher

Distances use simulator coordinate units, not verified metres.
"""

from __future__ import annotations

import json
from collections import defaultdict
from math import hypot, isfinite
from typing import Any, Iterable


PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

# Heuristic threshold, not a calibrated football pressure metric.
PRESSURE_RADIUS = 3.0

SPATIAL_VERSION = "1.0.0"


def _xy(value: Any) -> tuple[float, float]:
    """Extract and validate a player's X/Y coordinates."""

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
    """Infer a Footysim team from a player identifier."""

    if "_" not in player_id:
        raise ValueError(
            f"Cannot infer Footysim team from player ID: {player_id}"
        )

    return player_id.split("_", 1)[0]


def _payload(frame: dict) -> dict:
    """Accept canonical frames or streaming envelopes."""

    if "payload_json" in frame:
        inner = frame["payload_json"]

        if isinstance(inner, str):
            return json.loads(inner)

        if isinstance(inner, dict):
            return inner

        raise ValueError("Invalid payload_json")

    return frame


def spatial_sample(
    frame: dict,
    *,
    radius: float = PRESSURE_RADIUS,
    pitch_length: float = PITCH_LENGTH,
) -> dict | None:
    """
    Calculate spatial relationships around the ball carrier.

    Returns None when nobody possesses the ball.

    Pressure means at least one opposing player is within
    the configured radius. It does not prove a pressing action.
    """

    f = _payload(frame)

    if not (isfinite(radius) and isfinite(pitch_length)):
        raise ValueError("Radius and pitch length must be finite")

    if radius <= 0 or pitch_length <= 0:
        raise ValueError("Radius and pitch length must be positive")

    players = f.get("player_positions", f.get("players"))

    if not isinstance(players, dict):
        raise ValueError(
            "Frame lacks dictionary player_positions/players"
        )

    owner = f.get(
        "ball_owner_id",
        f.get("ball_owner", f.get("owner")),
    )

    if not owner:
        return None

    if owner not in players:
        raise ValueError(
            f"Owner {owner} not found among player positions"
        )

    ox, oy = _xy(players[owner])
    owner_team = _team_id(str(owner))

    all_opponents = []

    for player_id, position in players.items():

        if _team_id(str(player_id)) == owner_team:
            continue

        px, py = _xy(position)

        distance = hypot(
            px - ox,
            py - oy,
        )

        all_opponents.append(
            (str(player_id), round(distance, 4))
        )

    # Sort by nearest opponent, then player ID.
    all_opponents.sort(
        key=lambda item: (item[1], item[0])
    )

    nearby_opponents = [
        (player_id, distance)
        for player_id, distance in all_opponents
        if distance <= radius
    ]

    # Absolute pitch thirds, not attacking/defensive thirds.
    zone_index = min(
        2,
        max(
            0,
            int(ox / (pitch_length / 3.0))
        ),
    )

    return {
        "match_id": f.get("match_id"),
        "frame_id": f.get("frame_id"),
        "match_second": f.get(
            "match_second",
            f.get("t"),
        ),

        "ball_carrier_id": str(owner),
        "ball_carrier_team": owner_team,

        "absolute_pitch_third": (
            "left",
            "middle",
            "right",
        )[zone_index],

        "nearest_opponent_id": (
            all_opponents[0][0]
            if all_opponents
            else None
        ),

        "nearest_opponent_distance": (
            all_opponents[0][1]
            if all_opponents
            else None
        ),

        "nearby_opponent_count": len(nearby_opponents),

        "pressure_present": bool(nearby_opponents),

        "nearby_opponents": [
            player_id
            for player_id, _ in nearby_opponents
        ],
    }


def summarize_spatial_frames(
    frames: Iterable[dict],
    *,
    radius: float = PRESSURE_RADIUS,
) -> dict:
    """
    Produce offline spatial summaries.

    Used for local validation and testing.

    Live five-minute Gold aggregations will be calculated
    by Fabric KQL, not this function.
    """

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

        n = row["owned_frames"]

        zones.append(
            {
                "ball_carrier_team": team,
                "absolute_pitch_third": zone,
                **row,
                "pressure_exposure_rate": round(
                    row["pressured_frames"] / n,
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


def enrich_tracking_message(
    message: dict,
    *,
    radius: float = PRESSURE_RADIUS,
) -> dict:
    """
    Add spatial context to an existing tracking message.

    The original message and canonical frame fields
    remain unchanged.

    Spatial context is stored inside payload_json
    and transmitted through the existing frame route.
    """

    if message.get("record_type") != "frame":
        return message

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

    payload["spatial_context"] = spatial_context

    enriched_message = dict(message)

    enriched_message["payload_json"] = json.dumps(
        payload,
        separators=(",", ":"),
        allow_nan=False,
    )

    return enriched_message
