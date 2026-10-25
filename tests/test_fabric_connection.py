
import os
from pathlib import Path

from dotenv import load_dotenv
from azure.kusto.data import (
    KustoClient,
    KustoConnectionStringBuilder,
)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

QUERY_URI = os.getenv("FSI_KUSTO_QUERY_URI")
DATABASE = os.getenv("FSI_KUSTO_DATABASE", "fsi_db")

RUN_ID = "b916661b-1a33-413a-98a2-47595afded58"

if not QUERY_URI:
    raise RuntimeError("FSI_KUSTO_QUERY_URI is missing from .env")

# Reuse the authenticated Azure CLI session.
kcsb = KustoConnectionStringBuilder.with_az_cli_authentication(
    QUERY_URI
)

query = f"""
fsi_gold_match_stats("{RUN_ID}", 5400.0)
| project team_id,
          pass_attempts,
          pass_completions,
          pass_completion_pct,
          shots,
          goals,
          xg
| order by team_id asc
"""
print("Connecting to Fabric Eventhouse...")

with KustoClient(kcsb) as client:
    response = client.execute(DATABASE, query)
    table = response.primary_results[0]

    print(f"Rows returned: {len(table.rows)}")

    for row in table:
        print({
            "team_id": row["team_id"],
            "pass_attempts": row["pass_attempts"],
            "pass_completions": row["pass_completions"],
            "pass_completion_pct": row["pass_completion_pct"],
            "shots": row["shots"],
            "goals": row["goals"],
            "xg": row["xg"],
        })

print("Fabric connection successful.")