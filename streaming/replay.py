
import json
import time
import math
from datetime import datetime, timezone
from pathlib import Path

from streaming.replay_config import ReplayConfig

def load_replay_records(fixtures_dir):
    """Load and order the three canonical datasets."""
    fixtures_dir = Path(fixtures_dir)

    def read(filename):
        with (fixtures_dir / filename).open(
            encoding="utf-8"
        ) as file:
            return json.load(file)

    metadata = read("canonical_metadata.json")
    events = read("canonical_events.json")
    frames = read("canonical_frames.json")

    match_id = metadata["match_id"]

    records = []

    # Metadata is published at the start of the replay.
    records.append({
        "record_type": "metadata",
        "match_id": match_id,
        "tick": 0,
        "match_second": 0.0,
        "payload": metadata
    })

    for index, frame in enumerate(frames):
        if frame["match_id"] != match_id:
            raise ValueError("Frame match_id mismatch")

        records.append({
            "record_type": "frame",
            "match_id": match_id,
            "tick": frame["tick"],
            "match_second": frame["match_second"],
            "source_index": index,
            "payload": frame
        })

    for index, event in enumerate(events):
        if event["match_id"] != match_id:
            raise ValueError("Event match_id mismatch")

        records.append({
            "record_type": "event",
            "match_id": match_id,
            "tick": event["tick"],
            "match_second": event["match_second"],
            "source_index": index,
            "payload": event
        })

    # Deterministic ordering when records share a tick.
    priority = {
        "metadata": 0,
        "frame": 1,
        "event": 2
    }

    records.sort(
        key=lambda record: (
            record["tick"],
            priority[record["record_type"]],
            record.get("source_index", -1)
        )
    )

    return records


def replay( records, publish, speed=None, sleep=time.sleep,
            monotonic=time.monotonic, utcnow=None, config=None,):
    """Emit match records at the configured playback speed."""

    config = config or ReplayConfig()

    playback_speed = config.speed if speed is None else speed

    if not math.isfinite(playback_speed) or playback_speed <= 0:
        raise ValueError("Playback speed must be finite and positive")

    if utcnow is None:
        utcnow = lambda: datetime.now(timezone.utc)

    if not records:
        return

    start_second = records[0]["match_second"]
    start_wall = monotonic()

    previous_tick = -1
    previous_second = float("-inf")

    for record in records:
        tick = record["tick"]
        match_second = record["match_second"]

        if tick < previous_tick:
            raise ValueError("Records are not ordered by tick")

        if match_second < previous_second:
            raise ValueError("Match timestamps are not ordered")

        previous_tick = tick
        previous_second = match_second

        elapsed_match = match_second - start_second

        target_wall = start_wall + elapsed_match / playback_speed
        remaining = target_wall - monotonic()

        if remaining > 0:
            sleep(remaining)

        published = {
            **record,
            "emitted_at_utc": utcnow().isoformat()
        }

        publish(published)

