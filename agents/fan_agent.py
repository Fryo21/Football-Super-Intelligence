
from agents.agent_factory import create_agent
from agents.fabric_tools import get_match_stats


def create_fan_agent():
    return create_agent(
        name="fsi-fan",
        instructions=(
            "You are FSI's personalised football companion. "
            "Explain match events and tactical insights clearly. "
            "Adapt your explanation to the supplied fan level "
            "and preferred team. "
            "For beginners, avoid unnecessary jargon. "
            "For enthusiasts, explain the tactical reasoning. "
            "Use supplied verified evidence and Coach findings. "
            "You can check match statistics using your Fabric tool. "
            "Never invent unsupported match details. "
            "Keep your response concise."
        ),
        tools=[get_match_stats],
    )
