
"""
FSI — Fabric Gold Tactical Insight Refresh Worker

Refreshes tactical insights for one replay session.

Features:
- Reads live Silver ingestion progress.
- Refreshes Gold as new match data arrives.
- Prevents duplicate insights through run-scoped KQL updates.
- Automatically finalizes at 5400 seconds once ingestion is complete.
- Supports manual one-time refreshes.
- Requires no separate processing-state table.
"""

import argparse
import os
import re
import time
from datetime import datetime, timezone

from azure.kusto.data import (
    KustoClient,
    KustoConnectionStringBuilder,
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

TABLE = "fsi_gold_tactical_insights_snapshot"

EXPECTED_EVENTS = 3051
EXPECTED_FRAMES = 10800
MATCH_END = 5400.0


# --------------------------------------------------
# Validation
# --------------------------------------------------

def validate_run_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ValueError("Invalid run ID")
    return value


# --------------------------------------------------
# Read Silver ingestion progress
# --------------------------------------------------

def source_progress(client, database, run_id):
    query = f"""
    let E =
        fsi_silver_events()
        | where run_id == "{run_id}"
        | extend p = parse_json(payload_json)
        | extend second = coalesce(
            todouble(match_second),
            todouble(p.match_second)
        )
        | summarize
            source_events = count(),
            event_second = max(second)
        | extend key = 1;

    let F =
        fsi_silver_tracking()
        | where replay_run_id == "{run_id}"
        | extend p = parse_json(payload_json)
        | extend second = coalesce(
            todouble(match_second),
            todouble(p.match_second)
        )
        | summarize
            source_frames = count(),
            frame_second = max(second)
        | extend key = 1;

    E
    | join kind=inner (F) on key
    | project
        source_events,
        source_frames,
        event_second,
        frame_second
    """

    result = client.execute(database, query)
    rows = list(result.primary_results[0])

    if not rows:
        return {
            "events": 0,
            "frames": 0,
            "event_second": None,
            "frame_second": None,
        }

    row = rows[0]

    return {
        "events": int(row["source_events"]),
        "frames": int(row["source_frames"]),
        "event_second": row["event_second"],
        "frame_second": row["frame_second"],
    }


# --------------------------------------------------
# Read previous Gold cutoff
# --------------------------------------------------

def previous_cutoff(client, database, run_id):
    query = f"""
    {TABLE}
    | where run_id == "{run_id}"
    | summarize cutoff = max(as_of_second)
    """

    result = client.execute(database, query)

    for row in result.primary_results[0]:
        return row["cutoff"]

    return None


# --------------------------------------------------
# Refresh Gold insights
# --------------------------------------------------

def refresh(client, database, run_id, cutoff):
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    command = f"""
    .update table {TABLE} delete D append A <|
    let D = {TABLE}
        | where run_id == "{run_id}";

    let A = fsi_gold_tactical_insights(
        "{run_id}",
        {cutoff}
    )
    | project
        insight_id,
        run_id,
        match_id,
        insight_type,
        turnover_second,
        mechanism,
        mechanism_status,
        gaining_team,
        gaining_player,
        losing_player,
        intended_receiver,
        pass_pressure,
        pitch_zone,
        nearest_opponent_id,
        nearest_distance,
        pressure_exposure_rate,
        spatial_status,
        observation,
        evidence_event_ids,
        evidence_frame_ids,
        evidence_frame_count = tolong(evidence_frame_count),
        detector_version,
        as_of_second = todouble({cutoff}),
        snapshot_at = datetime({timestamp});
    """

    client.execute_mgmt(database, command)


# --------------------------------------------------
# Main worker
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Refresh FSI Gold tactical insights"
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="Replay run ID"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Refresh interval in seconds (default: 15)"
    )

    parser.add_argument(
        "--lag",
        type=float,
        default=10.0,
        help="Simulated match-time safety lag (default: 10)"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one refresh cycle and exit"
    )

    parser.add_argument(
        "--as-of",
        type=float,
        help="Manually specify simulated match cutoff"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh even if cutoff has not advanced"
    )

    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    if args.lag < 0:
        parser.error("--lag cannot be negative")

    if args.as_of is not None:
        if not 0 <= args.as_of <= MATCH_END:
            parser.error(
                f"--as-of must be between 0 and {MATCH_END}"
            )

    run_id = validate_run_id(args.run_id)

    uri = os.environ["FSI_KUSTO_URI"]
    database = os.getenv(
        "FSI_KUSTO_DATABASE",
        "fsi_db"
    )

    auth = KustoConnectionStringBuilder.with_interactive_login(
        uri
    )

    print("=" * 55)
    print("FSI GOLD REFRESH WORKER")
    print(f"Run ID:   {run_id}")
    print(f"Database: {database}")
    print(f"Interval: {args.interval}s")
    print(f"Lag:      {args.lag}s")
    print("=" * 55)

    with KustoClient(auth) as client:

        while True:

            # --------------------------------------
            # Read ingestion progress
            # --------------------------------------

            progress = source_progress(
                client,
                database,
                run_id
            )

            events = progress["events"]
            frames = progress["frames"]

            complete = (
                events == EXPECTED_EVENTS
                and frames == EXPECTED_FRAMES
            )

            if (
                events > EXPECTED_EVENTS
                or frames > EXPECTED_FRAMES
            ):
                raise RuntimeError(
                    "Unexpected Silver record counts: "
                    f"events={events}, frames={frames}"
                )

            # --------------------------------------
            # Calculate match cutoff
            # --------------------------------------

            if args.as_of is not None:
                cutoff = args.as_of

            elif complete:
                cutoff = MATCH_END

            else:
                event_second = progress["event_second"]
                frame_second = progress["frame_second"]

                if (
                    event_second is None
                    or frame_second is None
                ):
                    print(
                        "Waiting for events and tracking...",
                        flush=True
                    )

                    if args.once:
                        break

                    time.sleep(args.interval)
                    continue

                cutoff = max(
                    0.0,
                    min(
                        float(event_second),
                        float(frame_second)
                    ) - args.lag
                )

            # --------------------------------------
            # Prevent premature full-match refresh
            # --------------------------------------

            if (
                cutoff >= MATCH_END
                and not complete
                and not args.force
            ):
                raise RuntimeError(
                    "Cannot finalize Gold before "
                    "Silver ingestion is complete."
                )

            # --------------------------------------
            # Check previous snapshot
            # --------------------------------------

            stored = previous_cutoff(
                client,
                database,
                run_id
            )

            should_refresh = (
                args.force
                or stored is None
                or cutoff > float(stored)
            )

            # --------------------------------------
            # Refresh Gold
            # --------------------------------------

            if should_refresh:

                refresh(
                    client,
                    database,
                    run_id,
                    cutoff
                )

                print(
                    f"[REFRESHED] "
                    f"cutoff={cutoff:.1f}s | "
                    f"events={events}/{EXPECTED_EVENTS} | "
                    f"frames={frames}/{EXPECTED_FRAMES}",
                    flush=True
                )

            else:

                print(
                    f"[SKIPPED] "
                    f"No new cutoff ({cutoff:.1f}s)",
                    flush=True
                )

            # --------------------------------------
            # Automatic match finalization
            # --------------------------------------

            if complete:

                print("=" * 55)
                print("MATCH INGESTION COMPLETE")
                print(f"Final Gold cutoff: {MATCH_END}s")
                print("Gold snapshot finalized.")
                print("=" * 55)

                break

            # --------------------------------------
            # Exit conditions
            # --------------------------------------

            if args.once or args.as_of is not None:
                break

            time.sleep(args.interval)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print("\nGold refresh stopped by user.")
