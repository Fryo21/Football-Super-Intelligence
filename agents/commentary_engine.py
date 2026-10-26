
"""Generate commentary from verified Fabric match events."""

import asyncio
import json

from agents.live_commentary_agent import create_live_commentary_agent
from agents.commentary_selector import (
    get_commentary_events,
    select_commentary_moments,
    enrich_turnover_moments,
)
from agents.config import FSI_TEST_RUN_ID


async def generate_commentary(agent, moment):
    """Ask the Live Commentary Agent to narrate one verified moment."""

    evidence = {
        "match_second": moment["match_second"],
        "event_type": moment["event_type"],
        "team_id": moment["team_id"],
        "player_id": moment["player_id"],
        "outcome": moment["outcome"],
        "related_players": moment["related_players"],
        "evidence_event_ids": moment["evidence_event_ids"],
    }

    
    prompt = (
    "Generate ONE short, natural football commentary line "
    "for the following verified synthetic match moment.\n\n"
    f"{json.dumps(evidence, indent=2)}\n\n"
    "Rules:\n"
    "- Use only the supplied event facts.\n"
    "- Do not retrieve full-match statistics for this task.\n"
    "- Do not mention future events or the final score.\n"
    "- Do not invent names, actions, injuries or history.\n"
    "- RED_ST and similar values are identifiers, not names.\n"
    "- A shot outcome of parry means the shot was parried.\n"
    "- A turnover does not prove how possession was lost "
    "unless that information is supplied.\n"
    "- For turnovers, use turnover_context to identify who "
    "gained and lost possession. Never infer these roles "
    "from team_id or player_id alone.\n"
    "- If turnover_context is missing, do not identify "
    "which player or team lost possession.\n"
    "- Deliver expressive, engaging football broadcast commentary.\n"
    "- Use excitement, anticipation or dramatic emphasis when justified.\n"
    "- Sound like a professional commentator, not a match event log.\n"
    "- Use natural player descriptions when their positions are verified.\n"
    "- Keep commentary concise but emotionally engaging.\n"
    "- Keep the commentary to one or two sentences.\n"
    "- Return commentary text only."
)


    result = await agent.run(prompt)

    return {
        "match_second": moment["match_second"],
        "event_type": moment["event_type"],
        "priority": moment["priority"],
        "commentary_text": result.text.strip(),
        "evidence_event_ids": moment["evidence_event_ids"],
        "turnover_context": moment.get("turnover_context"),
    }


async def main():
    events = get_commentary_events(
        run_id=FSI_TEST_RUN_ID,
        start_second=0,
        end_second=900,
    )

    moments = select_commentary_moments(events)
    moments = enrich_turnover_moments(
    run_id=FSI_TEST_RUN_ID,
    moments=moments,
    as_of_second=900,
)

    print(f"Retrieved {len(events)} events")
    print(f"Selected {len(moments)} commentary moments")

    agent = create_live_commentary_agent()
    results = []

    # Initially test only three moments to control API usage.
    for moment in moments:
        commentary = await generate_commentary(agent, moment)
        results.append(commentary)

        print(
            json.dumps(commentary, indent=2, ensure_ascii=False)
        )

    print(f"\nGenerated {len(results)} commentary lines.")


if __name__ == "__main__":
    asyncio.run(main())
