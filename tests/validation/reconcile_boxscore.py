
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT / "data" / "sources" /
    "footysim" / "match_output.json"
)

with SOURCE.open(encoding="utf-8") as f:
    match = json.load(f)

counts = defaultdict(Counter)
xg = defaultdict(float)

for event in match["events_general"]:
    team = event.get("team")
    if not team:
        continue

    event_type = event["type"]
    counts[team][event_type] += 1

    if event_type == "shot":
        xg[team] += event.get("xg", 0.0)

comparisons = {
    "passes_attempted": "pass",
    "passes_completed": "pass_complete",
    "shots": "shot",
    "goals": "goal",
    "tackles_won": "tackle_won",
    "fouls": "foul",
    "yellow_cards": "yellow_card",
    "red_cards": "red_card",
}

mismatches = []

for team, box in match["boxscore"]["teams"].items():
    print(f"\nTEAM: {team}")
    print(f"{'Metric':<22} {'Events':>10} {'Boxscore':>10}")

    for metric, event_type in comparisons.items():
        calculated = counts[team][event_type]
        expected = box[metric]

        print(
            f"{metric:<22} "
            f"{calculated:>10} "
            f"{expected:>10}"
        )

        if calculated != expected:
            mismatches.append(
                (team, metric, calculated, expected)
            )

    calculated_xg = round(xg[team], 3)
    expected_xg = box["xg"]

    print(
        f"{'xg':<22} "
        f"{calculated_xg:>10.3f} "
        f"{expected_xg:>10.3f}"
    )

    if abs(calculated_xg - expected_xg) > 0.01:
        mismatches.append(
            (team, "xg", calculated_xg, expected_xg)
        )

print("\nReconciliation differences:", len(mismatches))

for row in mismatches:
    print("Mismatch:", row)
