
from pathlib import Path

from streaming.replay import load_replay_records, replay


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "data" / "fixtures"


def test_replay_order_and_counts():
    records = load_replay_records(FIXTURES)

    # 1 metadata + 3051 events + 10800 frames
    assert len(records) == 13852

    assert records[0]["record_type"] == "metadata"

    ticks = [record["tick"] for record in records]
    assert ticks == sorted(ticks)

    assert sum(
        r["record_type"] == "event" for r in records
    ) == 3051

    assert sum(
        r["record_type"] == "frame" for r in records
    ) == 10800

    assert "final_score" not in records[0]["payload"]

    match_ids = {r["match_id"] for r in records}
    assert len(match_ids) == 1


def test_replay_is_deterministic():
    first = load_replay_records(FIXTURES)
    second = load_replay_records(FIXTURES)

    assert first == second


def test_replay_timing():
    clock = [0.0]
    published = []

    records = [
        {
            "record_type": "metadata",
            "tick": 0,
            "match_second": 0.0,
            "payload": {}
        },
        {
            "record_type": "event",
            "tick": 20,
            "match_second": 2.0,
            "payload": {}
        },
        {
            "record_type": "frame",
            "tick": 40,
            "match_second": 4.0,
            "payload": {}
        }
    ]

    def fake_sleep(seconds):
        clock[0] += seconds

    def fake_monotonic():
        return clock[0]

    def publish(record):
        published.append(
            (record["match_second"], clock[0])
        )

    replay(
        records,
        publish=publish,
        speed=2.0,
        sleep=fake_sleep,
        monotonic=fake_monotonic
    )

    assert published == [
        (0.0, 0.0),
        (2.0, 1.0),
        (4.0, 2.0)
    ]
