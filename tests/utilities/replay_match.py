
import argparse
import json
from pathlib import Path


from config.paths import TEST_FIXTURES, REPLAY_OUTPUT
from streaming.replay import load_replay_records, replay


def main():
    parser = argparse.ArgumentParser(
        description="Replay Footysim records as a live-paced stream"
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=10.0,
        help="Playback speed multiplier"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of records to emit"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=REPLAY_OUTPUT
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    records = load_replay_records(
        TEST_FIXTURES
    )

    if args.limit is not None:
        records = records[:args.limit]

    args.output.parent.mkdir(
        parents=True, exist_ok=True
    )

    emitted = 0

    with args.output.open("w", encoding="utf-8") as file:

        def publish(record):
            nonlocal emitted

            file.write(
                json.dumps(record, separators=(",", ":"))
                + "\n"
            )
            file.flush()

            emitted += 1

            # Show metadata and football events.
            # Avoid flooding the console with frames.
            if record["record_type"] == "metadata":
                print("MATCH START:", record["match_id"])

            elif record["record_type"] == "event":
                event = record["payload"]

                print(
                    f"[{record['match_second']:7.1f}s] "
                    f"{event['event_type']:22} "
                    f"{event.get('player_id') or '-'}"
                )

        replay(
            records,
            publish=publish,
            speed=args.speed
        )

    print(f"\nPublished {emitted} records")
    print("Output:", args.output)


if __name__ == "__main__":
    main()

