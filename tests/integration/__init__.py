
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.eventhub import EventData, EventHubProducerClient


ROOT = Path(__file__).resolve().parents[1]

EVENTS_FILE = (
    ROOT / "tests" / "data" / "fixtures" /
    "canonical_events.json"
)


def create_message(event):
    """Convert an FSI event to the Eventhouse ingestion format."""

    return {
        "record_type": "event",
        "schema_version": event["schema_version"],
        "event_id": event["event_id"],
        "match_id": event["match_id"],
        "event_type": event["event_type"],
        "match_second": event["match_second"],
        "tick": event["tick"],
        "team_id": event["team_id"],
        "player_id": event["player_id"],
        "payload_json": json.dumps(
            event, separators=(",", ":")
        ),
        "emitted_at_utc": datetime.now(
            timezone.utc
        ).isoformat()
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.limit <= 0:
        parser.error("--limit must be positive")

    connection = os.environ.get(
        "FSI_EVENTSTREAM_CONNECTION"
    )

    if not connection:
        raise RuntimeError(
            "FSI_EVENTSTREAM_CONNECTION is missing"
        )

    with EVENTS_FILE.open(encoding="utf-8") as file:
        events = json.load(file)

    selected_events = events[:args.limit]

    if not selected_events:
        raise RuntimeError("No events available")

    sent = 0

    with EventHubProducerClient.from_connection_string(
        conn_str=connection.strip()
    ) as producer:

        batch = producer.create_batch()

        for event in selected_events:
            message = EventData(
                json.dumps(
                    create_message(event),
                    separators=(",", ":")
                )
            )

            try:
                batch.add(message)

            except ValueError:
                # Existing batch has reached its size limit.
                producer.send_batch(batch)

                batch = producer.create_batch()
                batch.add(message)

            sent += 1

        if len(batch) > 0:
            producer.send_batch(batch)

    print("Events sent:", sent)
    print("Match ID:", selected_events[0]["match_id"])
    print("First event ID:", selected_events[0]["event_id"])
    print("Last event ID:", selected_events[-1]["event_id"])


if __name__ == "__main__":
    main()
