
"""Read-only Microsoft Fabric tools for FSI agents."""

import json
import math
from uuid import UUID

from agent_framework import tool
from azure.kusto.data import (
    KustoClient,
    KustoConnectionStringBuilder,
)


from azure.identity import DefaultAzureCredential

from agents.config import FSI_KUSTO_URI, FSI_KUSTO_DATABASE


# Only these verified Gold functions can be called.
ALLOWED_GOLD_FUNCTIONS = {
    "fsi_gold_match_stats",
    "fsi_gold_pressure_shifts",
    "fsi_gold_turnover_intelligence",
    "fsi_gold_tactical_insights",
    "fsi_gold_player_influence",
    "fsi_gold_pass_quality",
}

MAX_MATCH_SECOND = 5400.0
MAX_RESULT_ROWS = 100


def _query_gold(
    function_name: str,
    run_id: str,
    as_of_second: float,
) -> str:
    """Execute an approved Gold function and return JSON."""

    if function_name not in ALLOWED_GOLD_FUNCTIONS:
        raise ValueError(
            f"Gold function is not approved: {function_name}"
        )

    # Validate parameters provided by the AI model.
    run_id = str(UUID(run_id))
    as_of_second = float(as_of_second)

    if (
        not math.isfinite(as_of_second)
        or not 0 <= as_of_second <= MAX_MATCH_SECOND
    ):
        raise ValueError(
            "as_of_second must be between 0 and 5400"
        )


    connection = (
        KustoConnectionStringBuilder.with_azure_token_credential(
            FSI_KUSTO_URI,
            DefaultAzureCredential(
                exclude_interactive_browser_credential=True
            ),
        )
    )

    # Query names are taken from our fixed allowlist.
    query = (
        f'{function_name}("{run_id}", {as_of_second})'
        f'\n| take {MAX_RESULT_ROWS + 1}'
    )

    with KustoClient(connection) as client:
        response = client.execute(
            FSI_KUSTO_DATABASE,
            query,
        )

        table = response.primary_results[0]
        columns = [
            column.column_name
            for column in table.columns
        ]

        rows = [
            {name: row[name] for name in columns}
            for row in table
        ]

    truncated = len(rows) > MAX_RESULT_ROWS
    rows = rows[:MAX_RESULT_ROWS]

    print(
        f"[FABRIC] {function_name} returned "
        f"{len(rows)} rows"
    )

    return json.dumps(
        {
            "source": "Microsoft Fabric Eventhouse",
            "gold_function": function_name,
            "run_id": run_id,
            "as_of_second": as_of_second,
            "returned_rows": len(rows),
            "truncated": truncated,
            "rows": rows,
        },
        default=str,
        allow_nan=False,
    )


@tool(approval_mode="never_require")
def get_match_stats(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve verified team passing, shooting, goals,
    expected goals, tackles, turnovers and discipline
    statistics at the requested match time.
    """
    return _query_gold(
        "fsi_gold_match_stats", run_id, as_of_second
    )


@tool(approval_mode="never_require")
def get_pressure_shifts(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve changes in high-pressure pass rates across
    consecutive five-minute windows.

    These measurements describe pressure experienced by
    passers. They do not alone prove which opponent caused
    the pressure or why the pressure changed.
    """
    return _query_gold(
        "fsi_gold_pressure_shifts", run_id, as_of_second
    )


@tool(approval_mode="never_require")
def get_turnover_intelligence(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve turnover mechanisms, preceding pass evidence,
    player identifiers and available spatial context.

    Distinguish confirmed simulator mechanisms from
    incomplete or missing spatial evidence.
    """
    return _query_gold(
        "fsi_gold_turnover_intelligence",
        run_id,
        as_of_second,
    )


@tool(approval_mode="never_require")
def get_tactical_insights(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve evidence-backed turnover observations with
    event IDs, tracking frame IDs and spatial status.

    These are turnover-context insights, not a complete
    analysis of team formations or tactical systems.
    """
    return _query_gold(
        "fsi_gold_tactical_insights",
        run_id,
        as_of_second,
    )


@tool(approval_mode="never_require")
def get_player_influence(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve player event contributions including passes,
    tackles, interceptions, shots, goals and defensive
    proximity observations.

    Proximity observations are not direct proof of
    successful defending.
    """
    return _query_gold(
        "fsi_gold_player_influence",
        run_id,
        as_of_second,
    )


@tool(approval_mode="never_require")
def get_pass_quality(
    run_id: str,
    as_of_second: float,
) -> str:
    """Retrieve measured passing-quality indicators from
    the Fabric Gold passing analytics.

    Interpret only metrics actually present in the result.
    """
    return _query_gold(
        "fsi_gold_pass_quality",
        run_id,
        as_of_second,
    )
