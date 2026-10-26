
"""Read-only event selection for FSI football commentary."""

import json
import math
from uuid import UUID

from azure.identity import DefaultAzureCredential
from azure.kusto.data import (
    KustoClient,
    KustoConnectionStringBuilder,
)

from agents.config import FSI_KUSTO_URI, FSI_KUSTO_DATABASE


PRIORITY = {
    "goal": "critical",
    "red_card": "critical",
    "shot": "high",
    "save": "high",
    "yellow_card": "medium",
    "turnover": "medium",
}

MAX_EVENTS = 500


def get_commentary_events(
    run_id: str,
    start_second: float = 0,
    end_second: float = 5400,
):
    """Retrieve verified events from the Fabric Silver layer."""

    run_id = str(UUID(run_id))
    start_second = float(start_second)
    end_second = float(end_second)

    if not (
        math.isfinite(start_second)
        and math.isfinite(end_second)
        and 0 <= start_second <= end_second <= 5400
    ):
        raise ValueError("Invalid match-time range")

    kql = f'''
    fsi_silver_events()
    | where run_id == "{run_id}"
    | where match_second between ({start_second} .. {end_second})
    | where event_type in (
        "goal", "shot", "save",
        "red_card", "yellow_card", "turnover"
    )
    | project match_second, event_id,
              event_type, team_id, player_id, payload_json
    | order by match_second asc, event_id asc
    | take {MAX_EVENTS + 1}
    '''

    credential = DefaultAzureCredential(
        exclude_interactive_browser_credential=True
    )

    connection = (
        KustoConnectionStringBuilder.with_azure_token_credential(
            FSI_KUSTO_URI, credential
        )
    )

    with KustoClient(connection) as client:
        response = client.execute(FSI_KUSTO_DATABASE, kql)
        rows = list(response.primary_results[0])

    if len(rows) > MAX_EVENTS:
        raise ValueError(
            "Too many events for one batch. "
            "Use a smaller match-time window."
        )

    events = []
    for row in rows:
        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload) if payload else {}

        events.append({
            "match_second": float(row["match_second"]),
            "event_id": str(row["event_id"]),
            "event_type": str(row["event_type"]),
            "team_id": str(row["team_id"]),
            "player_id": str(row["player_id"]),
            "payload": payload,
        })

    return events


def select_commentary_moments(events):
    """Combine related events and create commentary-ready moments."""

    events = sorted(
        events,
        key=lambda event: (
            event["match_second"],
            event["event_id"],
        ),
    )

    moments = []
    consumed = set()

    for index, event in enumerate(events):
        if event["event_id"] in consumed:
            continue

        event_type = event["event_type"]
        evidence = [event["event_id"]]
        combined_type = event_type
        finish_second = event["match_second"]
        related_players = {}

        if event_type == "shot":
            shot_outcome = event["payload"].get("outcome")

            # Match a subsequent save only when the shot outcome
            # explicitly confirms a save.
            if shot_outcome == "save":
                for following in events[index + 1:]:
                    difference = (
                        following["match_second"]
                        - event["match_second"]
                    )

                    if difference > 3:
                        break

                    if (
                        following["event_type"] == "save"
                        and following["event_id"] not in consumed
                        and following["team_id"] != event["team_id"]
                    ):
                        evidence.append(following["event_id"])
                        consumed.add(following["event_id"])
                        combined_type = "shot_saved"
                        finish_second = following["match_second"]
                        related_players["goalkeeper_id"] = (
                            following["player_id"]
                        )
                        break

        moments.append({
            "match_second": finish_second,
            "event_type": combined_type,
            "priority": PRIORITY[event_type],
            "team_id": event["team_id"],
            "player_id": event["player_id"],
            "outcome": event["payload"].get("outcome"),
            "evidence_event_ids": evidence,
            "related_players": related_players,
        })

        consumed.add(event["event_id"])

    return sorted(
        moments,
        key=lambda moment: moment["match_second"],
    )


if __name__ == "__main__":
    from agents.config import FSI_TEST_RUN_ID

    events = get_commentary_events(
        run_id=FSI_TEST_RUN_ID,
        start_second=0,
        end_second=900,
    )

    moments = select_commentary_moments(events)

    print(json.dumps(moments[:20], indent=2))
    print(f"\nEvents retrieved: {len(events)}")
    print(f"Commentary moments: {len(moments)}")

def enrich_turnover_moments(run_id, moments, as_of_second):
    """Attach verified Gold turnover context to selected moments."""
    import json

    from agents.fabric_tools import _query_gold

    if not any(m["event_type"] == "turnover" for m in moments):
        return moments

    gold_response = json.loads(
        _query_gold(
            "fsi_gold_tactical_insights",
            run_id,
            as_of_second,
        )
    )

    if gold_response.get("truncated"):
        raise RuntimeError(
            "Gold insights were truncated; turnover evidence may be incomplete."
        )

    insights_by_event_id = {}

    for insight in gold_response["rows"]:
        if insight.get("insight_type") != "turnover_context":
            continue

        for event_id in insight.get("evidence_event_ids", []):
            insights_by_event_id[str(event_id)] = insight

    for moment in moments:
        if moment["event_type"] != "turnover":
            continue

        insight = next(
            (
                insights_by_event_id[event_id]
                for event_id in moment["evidence_event_ids"]
                if event_id in insights_by_event_id
                and abs(
                    float(
                        insights_by_event_id[event_id]["turnover_second"]
                    ) - float(moment["match_second"])
                ) < 0.01
            ),
            None,
        )

        if insight is None:
            moment["turnover_context"] = None
            continue

        moment["turnover_context"] = {
            "gaining_team": insight.get("gaining_team"),
            "gaining_player": insight.get("gaining_player"),
            "losing_player": insight.get("losing_player"),
            "mechanism": insight.get("mechanism"),
            "mechanism_status": insight.get("mechanism_status"),
        }

    return moments
