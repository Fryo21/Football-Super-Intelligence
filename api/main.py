
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
from api.intelligence import router as intelligence_router

from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

QUERY_URI = os.getenv("FSI_KUSTO_URI")
DATABASE = os.getenv("FSI_KUSTO_DATABASE", "fsi_db")

if not QUERY_URI:
    raise RuntimeError("FSI_KUSTO_URI is missing")

app = FastAPI(
    title="FSI Football Intelligence API",
    version="0.1.0",
    description="Read-only football intelligence from Microsoft Fabric",
)
app.include_router(intelligence_router)


kcsb = KustoConnectionStringBuilder.with_azure_token_credential(
    QUERY_URI,
    DefaultAzureCredential(
        exclude_interactive_browser_credential=True
    ),
)

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


@app.get(
    "/api/v1/matches/{run_id}/stats",
    operation_id="get_match_stats",
    tags=["Football Intelligence"],
)
def get_match_stats(
    run_id: str,
    as_of_second: float = Query(
        ..., ge=0, le=5400,
        description="Match-time cutoff in seconds",
    ),
):
    # Keep both values constrained before constructing KQL.
    import re

    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}",
        run_id,
    ):
        raise HTTPException(422, "Invalid replay run ID")

    kql = f'''
    fsi_gold_match_stats("{run_id}", {as_of_second})
    | project team_id, pass_attempts, pass_completions,
              pass_completion_pct, shots, goals, xg
    | order by team_id asc
    '''

    try:
        with KustoClient(kcsb) as client:
            response = client.execute(DATABASE, kql)
            teams = [
                {
                    "team_id": row["team_id"],
                    "pass_attempts": row["pass_attempts"],
                    "pass_completions": row["pass_completions"],
                    "pass_completion_pct": row["pass_completion_pct"],
                    "shots": row["shots"],
                    "goals": row["goals"],
                    "xg": row["xg"],
                }
                for row in response.primary_results[0]
            ]
    except Exception:
        # Log details internally in a later production deployment.
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve match statistics",
        )

    return {
        "run_id": run_id,
        "as_of_second": as_of_second,
        "teams": teams,
    }
