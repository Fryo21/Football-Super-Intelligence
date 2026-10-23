
import argparse
import json
import os
import uuid
import logging
from pathlib import Path

from azure.eventhub import EventData, EventHubProducerClient

from analytics.tracking_spatial_analysis import enrich_tracking_message
from config.paths import MATCH_STORAGE
from config.logging_config import configure_logging
from streaming.replay import load_replay_records, replay
from streaming.replay_config import ReplayConfig


logger = logging.getLogger("fsi.streaming")

def make_message(record, run_id):
    """Build a Fabric ingestion envelope."""

    payload = record["payload"]
    kind = record["record_type"]

    message = {
        "record_type": kind,
        "schema_version": payload["schema_version"],
        "match_id": record["match_id"],
        "run_id": run_id,
        "match_second": record["match_second"],
        "tick": record["tick"],
        "emitted_at_utc": record["emitted_at_utc"],

        "event_id": "",
        "event_type": "",
        "team_id": "",
        "player_id": "",
        "frame_id": "",
        "ball_owner_id": "",
        "ball_position_json": "",
        "player_positions_json": "",
        "payload_json": ""
    }

    if kind == "event":
        message.update({
            "event_id": payload["event_id"],
            "event_type": payload["event_type"],
            "team_id": payload.get("team_id") or "",
            "player_id": payload.get("player_id") or ""
        })

    elif kind == "frame":
        message.update({
            "frame_id": payload["frame_id"],
            "ball_owner_id": payload.get("ball_owner_id") or "",
            "ball_position_json": json.dumps(
                payload["ball_position"]
            ),
            "player_positions_json": json.dumps(
                payload["player_positions"]
            )
        })

    message["payload_json"] = json.dumps(
        {**payload, "run_id": run_id},
        separators=(",", ":")
    )

    return message



def main():
    """Publish a prepared match to Microsoft Fabric Eventstream."""

    parser = argparse.ArgumentParser(
        description="Publish an FSI match to Microsoft Fabric"
    )

    parser.add_argument("--preparation-id", required=True)
    parser.add_argument("--speed", type=float, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--run-id", default=None)

    args = parser.parse_args()

    configure_logging()

    run_id = args.run_id or str(uuid.uuid4())

    counts = {
        "metadata": 0,
        "event": 0,
        "frame": 0,
    }

    match_id = None
    last_attempted = None
    last_published = None

    logger.info(
        "STREAM_RUN_STARTED run_id=%s preparation_id=%s",
        run_id,
        args.preparation_id,
    )

    try:
        if args.limit is not None and args.limit <= 0:
            raise ValueError("--limit must be positive")

        config = (
            ReplayConfig(speed=args.speed)
            if args.speed is not None
            else ReplayConfig()
        )

        preparation_id = str(uuid.UUID(args.preparation_id))
        match_directory = MATCH_STORAGE / preparation_id

        if not match_directory.is_dir():
            raise FileNotFoundError(
                f"Prepared match not found: {match_directory}"
            )

        records = load_replay_records(match_directory)

        if not records:
            raise ValueError("Prepared match contains no records")

        if args.limit is not None:
            records = records[:args.limit]

        match_id = records[0]["match_id"]

        logger.info(
            "STREAM_RECORDS_READY run_id=%s match_id=%s "
            "records=%d speed=%.2f",
            run_id,
            match_id,
            len(records),
            config.speed,
        )

        connection = os.getenv("FSI_EVENTSTREAM_CONNECTION")

        if not connection or not connection.strip():
            raise RuntimeError(
                "FSI_EVENTSTREAM_CONNECTION is missing"
            )

        with EventHubProducerClient.from_connection_string(
            conn_str=connection.strip()
        ) as producer:

            logger.info(
                "EVENTHUB_PRODUCER_INITIALIZED run_id=%s",
                run_id,
            )

            def publish(record):
                nonlocal last_attempted, last_published

                kind = record["record_type"]

                last_attempted = {
                    "type": kind,
                    "tick": record["tick"],
                    "match_second": record["match_second"],
                    "record_id": (
                        record["payload"].get("event_id")
                        or record["payload"].get("frame_id")
                        or record["match_id"]
                    ),
                }

                message = make_message(record, run_id)

                if kind == "frame":
                    message = enrich_tracking_message(message)

                batch = producer.create_batch()

                batch.add(
                    EventData(
                        json.dumps(
                            message,
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                    )
                )

                producer.send_batch(batch)

                counts[kind] += 1
                last_published = last_attempted.copy()

                total = sum(counts.values())

                if total % 500 == 0:
                    logger.info(
                        "STREAM_PROGRESS run_id=%s "
                        "published=%d scheduled=%d "
                        "match_second=%.1f",
                        run_id,
                        total,
                        len(records),
                        record["match_second"],
                    )

            replay(
                records,
                publish=publish,
                config=config,
            )

        logger.info(
            "STREAM_RUN_COMPLETED run_id=%s match_id=%s "
            "metadata=%d events=%d frames=%d",
            run_id,
            match_id,
            counts["metadata"],
            counts["event"],
            counts["frame"],
        )

    except Exception:
        logger.exception(
            "STREAM_RUN_FAILED run_id=%s match_id=%s "
            "published=%s last_attempted=%s "
            "last_published=%s",
            run_id,
            match_id or "unknown",
            counts,
            last_attempted,
            last_published,
        )
        raise


if __name__ == "__main__":
    main()


