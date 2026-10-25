
import json

from agents.config import (
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


TOOLS = [
    get_match_stats,
    get_pressure_shifts,
    get_turnover_intelligence,
    get_tactical_insights,
    get_player_influence,
    get_pass_quality,
]


def main():
    failures = []

    for function in TOOLS:
        name = function.name

        print(f"\n[TEST] {name}")

        try:
            result = function(
                run_id=FSI_TEST_RUN_ID,
                as_of_second=FSI_TEST_AS_OF_SECOND,
            )

            data = json.loads(result)
            rows = data["rows"]

            print(f"[PASS] {name}")
            print(f"Rows: {len(rows)}")
            print(f"Truncated: {data['truncated']}")

            if rows:
                print("Fields:", list(rows[0].keys()))
                print(
                    "First row:",
                    json.dumps(rows[0], default=str)[:1200],
                )
            else:
                print("No observations returned.")

        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            failures.append(name)

    print("\n=== TEST SUMMARY ===")
    print(f"Passed: {len(TOOLS) - len(failures)}")
    print(f"Failed: {len(failures)}")

    if failures:
        raise SystemExit(
            "Failed tools: " + ", ".join(failures)
        )


if __name__ == "__main__":
    main()
