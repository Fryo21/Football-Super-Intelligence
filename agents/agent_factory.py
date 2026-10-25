
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

from agents.config import FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL

from agents.fabric_tools import (
    get_match_stats,
    get_pressure_shifts,
    get_turnover_intelligence,
    get_tactical_insights,
    get_player_influence,
    get_pass_quality,
)


def create_agent(name: str, instructions: str, tools=None):
    client = FoundryChatClient(
        project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
        model=FOUNDRY_MODEL,
        credential=DefaultAzureCredential(
            exclude_interactive_browser_credential=True
        ),
    )

    return Agent(
        client=client,
        name=name,
        instructions=instructions,
        tools=tools or [],
    )


def create_coach_agent():
    return create_agent(
        "fsi-coach",
        (
            "You are FSI's football tactical analyst. "
            "Use Fabric tools to investigate match performance, "
            "pressure, turnovers and tactical observations. "
            "High-pressure rates measure pressure EXPERIENCED "
            "by a passing team, not pressure applied by that team. "
            "Separate verified facts from tactical hypotheses. "
            "Give practical recommendations with evidence. "
            "Do not invent statistics, formations or events."
        ),
        tools=[
            get_match_stats,
            get_pressure_shifts,
            get_turnover_intelligence,
            get_tactical_insights,
            get_player_influence,
            get_pass_quality,
        ],
    )
