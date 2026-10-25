
from agents.agent_factory import create_agent
from agents.fabric_tools import (
    get_match_stats,
    get_tactical_insights,
)


def create_broadcast_agent():
    return create_agent(
        name="fsi-broadcast",
        instructions=(
            "You are FSI's professional football broadcast analyst. "
            "Create engaging, accurate match commentary and recaps. "
            "Use supplied Coach findings as context, and verify "
            "match facts with your Fabric tools when necessary. "
            "Explain important moments in natural broadcast language. "
            "Do not invent goals, player names, match events or "
            "causal explanations. "
            "Keep the main recap concise, approximately 150 words."
        ),
        tools=[
            get_match_stats,
            get_tactical_insights,
        ],
    )
