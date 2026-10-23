
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from azure.eventhub import EventHubProducerClient, EventData


ROOT = Path(__file__).resolve().parents[2]

connection_string = os.environ.get(
    "FSI_EVENTSTREAM_CONNECTION"
)

if not connection_string:
    raise RuntimeError(
        "FSI_EVENTSTREAM_CONNECTION is not configured"
    )

events_path = (
    ROOT / "tests" / "data" / "fixtures" /
    "canonical_events.json"
)

with events_path.open(encoding="utf-8") as file:
    events = json.load(file)

# Use the first football event as our connection test.
event = events[0]

message = {
    "record_type": "event",
    "schema_version": event["schema_version"],
    "event_id": event["event_id"],
    "match_id": event["match_id"],
    "event_type": event["event_type"],
    "match_second": event["match_second"],
    "tick": event["tick"],
    "team_id": event["team_id"],
    "player_id": event["player_id"],
    "payload_json": json.dumps(event),
    "emitted_at_utc": datetime.now(
        timezone.utc
    ).isoformat()
}

with EventHubProducerClient.from_connection_string(
    conn_str=connection_string
) as producer:

    batch = producer.create_batch()

    batch.add(EventData(json.dumps(message)))

    producer.send_batch(batch)

print("Sent first canonical match event to Fabric.")
print("Event ID:", event["event_id"])
print("Match ID:", event["match_id"])