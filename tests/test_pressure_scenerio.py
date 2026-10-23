
import argparse
import json
import os
import uuid
from datetime import datetime, timezone

from azure.eventhub import EventData, EventHubProducerClient

MATCH_ID = "fsi_controlled_pressure_v1"


def make_event(run_id, index, match_second, pressure):
    event_id = f"{run_id}_pass_{index:03d}"
    tick = round(match_second * 10)

    payload = {
        "schema_version": "1.0",
        "run_id": run_id,
        "match_id": MATCH_ID,
        "event_id": event_id,
        "event_type": "pass",
        "team_id": "RED",
        "player_id": "RED_01",
        "match_second": float(match_second),
        "tick": tick,
        "pressure": float(pressure),
    }

    return {
        "record_type": "event",
        "run_id": run_id,
        "match_id": MATCH_ID,
        "event_id": event_id,
        "event_type": "pass",
        "team_id": "RED",
        "player_id": "RED_01",
        "match_second": float(match_second),
        "tick": tick,
        "payload_json": json.dumps(payload),
        "emitted_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def build_scenario(run_id):
    records = []

    # Previous window: 20-25 min, 3/20 under high pressure.
    for i in range(20):
        pressure = 0.8 if i < 3 else 0.2
        records.append(
            make_event(run_id, i, 1205 + i * 10, pressure)
        )

    # Current window: 25-30 min, 12/20 under high pressure.
    for i in range(20):
        pressure = 0.8 if i < 12 else 0.2
        records.append(
            make_event(run_id, i + 20, 1505 + i * 10, pressure)
        )

    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    run_id = "fsi_pressure_" + uuid.uuid4().hex[:12]
    records = build_scenario(run_id)

    print(f"RUN_ID={run_id}")
    print("Expected: 40 passes, 3/20 -> 12/20")
    print("Expected pressure increase: 45 percentage points")

    if not args.publish:
        print("Dry run complete; nothing sent to Fabric.")
        return

    connection = os.environ.get("FSI_EVENTSTREAM_CONNECTION")
    if not connection:
        raise RuntimeError(
            "FSI_EVENTSTREAM_CONNECTION is not configured"
        )

    with EventHubProducerClient.from_connection_string(
        conn_str=connection
    ) as producer:
        for record in records:
            batch = producer.create_batch()
            batch.add(EventData(json.dumps(record)))
            producer.send_batch(batch)

    print(f"Published {len(records)} events")
    print(f"Use this run ID in Fabric: {run_id}")


if __name__ == "__main__":
    main()
