
"""Resolve shared file paths for the FSI application."""

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


def resolve_path(name: str, default: str) -> Path:
    """Resolve an environment path against the project root."""

    path = Path(os.getenv(name, default)).expanduser()

    if path.is_absolute():
        return path

    return ROOT / path


FOOTYSIM_INPUT = resolve_path(
    "FSI_FOOTYSIM_INPUT",
    "data/sources/footysim/match_output.json",
)

MATCH_STORAGE = resolve_path(
    "FSI_MATCH_STORAGE",
    "data/runtime/matches",
)

TEST_FIXTURES = resolve_path(
    "FSI_TEST_FIXTURES",
    "tests/data/fixtures",
)

REPLAY_OUTPUT = resolve_path(
    "FSI_REPLAY_OUTPUT",
    "data/runtime/replay_output.jsonl",
)

SCHEMA_DIR = resolve_path(
    "FSI_SCHEMA_DIR",
    "data/schemas/v1",
)

LOG_DIR = resolve_path(
    "FSI_LOG_DIR",
    "data/runtime/logs",
)
