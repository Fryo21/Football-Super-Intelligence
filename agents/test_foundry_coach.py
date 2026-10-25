
import asyncio

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from agents.config import (
    FOUNDRY_PROJECT_ENDPOINT,
    FOUNDRY_MODEL,
    FSI_TEST_RUN_ID,
    FSI_TEST_AS_OF_SECOND,
)
from agents.fabric_tools import (
    get_match_stats,
    get_pressure_shifts,
    get_turnover_intelligence,
    get_tactical_insights,
    get_player_influence,
    get_pass_quality,
)


async def main():
    if not FOUNDRY_PROJECT_ENDPOINT or not FOUNDRY_MODEL:
        raise RuntimeError(
            "Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env"
        )

    coach = Agent(
        client=FoundryChatClient(
            project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
            model=FOUNDRY_MODEL,
            credential=AzureCliCredential(),
        ),
        name="fsi-coach",
        instructions=(
            "You are FSI's tactical football Coach Agent. "
            "Always call get_match_stats before analysing a match. "
            "Base your answer on returned data. "
            "Never invent statistics. "
            "Distinguish evidence from tactical interpretation."
        ),
        tools=[ get_match_stats,
                get_pressure_shifts,
                get_turnover_intelligence,
                get_tactical_insights,
                get_player_influence,
                get_pass_quality,
            ],
    )

    print("[FOUNDRY] Starting Coach Agent...")

    response = await coach.run(
        f"Analyse run_id={FSI_TEST_RUN_ID} "
        f"at as_of_second={FSI_TEST_AS_OF_SECOND}. "
        "Explain why BLU struggled against RED. "
        "Use match statistics, pressure shifts, turnover intelligence, "
        "and tactical insights to support your explanation. "
        "Recommend two possible tactical adjustments for BLU. "
        "Clearly distinguish verified evidence from hypotheses."
    )

    print("\n=== FSI COACH AGENT ===")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
