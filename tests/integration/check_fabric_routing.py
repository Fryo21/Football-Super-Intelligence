
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from azure.eventhub import EventData, EventHubProducerClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streaming.replay import load_replay_records
from stream_full_match import make_message


connection = os.environ["FSI_EVENTSTREAM_CONNECTION"]

records = load_replay_records(ROOT / "tests" / "data" / "fixtures")

samples = []

for kind in ("metadata", "event", "frame"):
    samples.append(
        next(r for r in records if r["record_type"] == kind)
    )

run_id = str(uuid.uuid4())

with EventHubProducerClient.from_connection_string(
    conn_str=connection.strip()
) as producer:

    for record in samples:
        item = {
            **record,
            "emitted_at_utc": datetime.now(
                timezone.utc
            ).isoformat()
        }

        message = make_message(item, run_id)

        batch = producer.create_batch()
        batch.add(EventData(json.dumps(message)))
        producer.send_batch(batch)

        print("Sent:", record["record_type"])

print("Routing test Run ID:", run_id)
