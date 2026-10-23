
import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from azure.eventhub import EventData, EventHubProducerClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streaming.replay import replay
from tests.integration.send_fabric_events import create_message


EVENTS_FILE = (
    ROOT / "tests" / "data" / "fixtures" /
    "canonical_events.json"
)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start", type=int, default=200)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--speed", type=float, default=100.0)

    # An omitted run ID creates a new session.
    # Supplying the same ID allows testing retries.
    parser.add_argument("--run-id", type=str, default=None)

    args = parser.parse_args()

    if args.start < 0:
        parser.error("--start must be non-negative")

    if args.limit <= 0:
        parser.error("--limit must be positive")

    if args.speed <= 0:
        parser.error("--speed must be positive")

    run_id = args.run_id or str(uuid.uuid4())

    connection = os.environ.get(
        "FSI_EVENTSTREAM_CONNECTION"
    )

    if not connection:
        raise RuntimeError(
            "FSI_EVENTSTREAM_CONNECTION is missing"
        )

    with EVENTS_FILE.open(encoding="utf-8") as file:
        events = json.load(file)

    selected = events[
        args.start:args.start + args.limit
    ]

    if not selected:
        raise RuntimeError("No events selected")

    records = [
        {
            "record_type": "event",
            "match_id": event["match_id"],
            "tick": event["tick"],
            "match_second": event["match_second"],
            "payload": event
        }
        for event in selected
    ]

    sent = 0

    print("Replay Run ID:", run_id)
    print("Match ID:", selected[0]["match_id"])
    print("Selected events:", len(selected))

    with EventHubProducerClient.from_connection_string(
        conn_str=connection.strip()
    ) as producer:

        def publish(record):
            nonlocal sent

            event = record["payload"]

            # Use the existing Eventhouse envelope.
            message = create_message(event)

            # Keep the original canonical event unchanged.
            # Add replay identity inside payload_json.
            payload = json.loads(message["payload_json"])
            payload["run_id"] = run_id

            message["payload_json"] = json.dumps(
                payload,
                separators=(",", ":")
            )

            message["emitted_at_utc"] = (
                record["emitted_at_utc"]
            )

            batch = producer.create_batch()
            batch.add(
                EventData(
                    json.dumps(message, separators=(",", ":"))
                )
            )

            producer.send_batch(batch)

            sent += 1

            print(
                f"[{event['match_second']:7.1f}s] "
                f"{event['event_type']:22} "
                f"{event['event_id']}"
            )

        replay(
            records,
            publish=publish,
            speed=args.speed
        )

    print("\nReplay completed")
    print("Run ID:", run_id)
    print("Events sent:", sent)


if __name__ == "__main__":
    main()

