
from agents.agent_factory import create_coach_agent
from agents.broadcast_agent import create_broadcast_agent
from agents.fan_agent import create_fan_agent


async def run_fsi_workflow(
    run_id: str,
    as_of_second: float,
    fan_level: str = "beginner",
    preferred_team: str = "BLU",
):
    shared_context = (
        f"Match run_id={run_id}, "
        f"as_of_second={as_of_second}. "
        "Only analyse events up to this cutoff. "
    )

    coach = create_coach_agent()
    broadcast = create_broadcast_agent()
    fan = create_fan_agent()

    coach_result = await coach.run(
        shared_context
        + "Retrieve verified data and explain the main "
        "tactical situation. Give one recommendation. "
        "Include supporting statistics and evidence IDs."
    )

    coach_text = coach_result.text

    broadcast_result = await broadcast.run(
        shared_context
        + "Write a concise broadcast match recap. "
        + "Use this Coach analysis as context, but "
        + "verify key facts with your tools:\n"
        + coach_text
    )

    fan_result = await fan.run(
        shared_context
        + f"Fan level: {fan_level}. "
        + f"Preferred team: {preferred_team}. "
        + "Explain the match situation using this "
        + "Coach analysis and broadcast recap:\n"
        + coach_text
        + "\n\nBroadcast recap:\n"
        + broadcast_result.text
    )

    return {
        "run_id": run_id,
        "as_of_second": as_of_second,
        "coach": coach_text,
        "broadcast": broadcast_result.text,
        "fan": fan_result.text,
        "handoffs": [
            "Coach -> Broadcast",
            "Coach + Broadcast -> Fan",
        ],
    }
