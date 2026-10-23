
"""Prepare Footysim match data for canonical replay."""

import argparse
import json
import logging
import uuid
from pathlib import Path

from config.paths import FOOTYSIM_INPUT, MATCH_STORAGE
from config.logging_config import configure_logging
from data.adapters.footysim_adapter import FootysimAdapter


logger = logging.getLogger("fsi.prepare_match")


def write_json(path: Path, data: object) -> None:
    """Write structured data to a JSON file."""

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, allow_nan=False)


def prepare_match(
    input_path: Path = FOOTYSIM_INPUT,
    output_root: Path = MATCH_STORAGE,
) -> Path:
    """Transform and store a simulated match for replay."""

    preparation_id = str(uuid.uuid4())
    match_dir = output_root / preparation_id
    match_id = None

    logger.info(
        "MATCH_PREPARATION_STARTED preparation_id=%s source=%s",
        preparation_id,
        input_path,
    )

    try:
        with input_path.open("r", encoding="utf-8") as file:
            raw_match = json.load(file)

        adapter = FootysimAdapter(raw_match)
        match_id = adapter.match_id

        events = adapter.transform_events()
        frames = adapter.transform_frames()
        metadata = adapter.transform_metadata()

        match_dir.mkdir(parents=True, exist_ok=False)

        write_json(match_dir / "raw_match.json", raw_match)
        write_json(match_dir / "canonical_events.json", events)
        write_json(match_dir / "canonical_frames.json", frames)
        write_json(match_dir / "canonical_metadata.json", metadata)

        manifest = {
            "preparation_id": preparation_id,
            "match_id": match_id,
            "source": "footysim",
            "schema_version": adapter.SCHEMA_VERSION,
            "event_count": len(events),
            "frame_count": len(frames),
            "status": "prepared",
        }

        write_json(match_dir / "manifest.json", manifest)

        logger.info(
            "MATCH_PREPARATION_COMPLETED "
            "preparation_id=%s match_id=%s "
            "events=%d frames=%d output=%s",
            preparation_id,
            match_id,
            len(events),
            len(frames),
            match_dir,
        )

        return match_dir

    except Exception:
        logger.exception(
            "MATCH_PREPARATION_FAILED "
            "preparation_id=%s match_id=%s output=%s",
            preparation_id,
            match_id or "unknown",
            match_dir,
        )
        raise



def main() -> None:
    """Read preparation arguments and generate canonical match files."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        type=Path,
        default=FOOTYSIM_INPUT,
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=MATCH_STORAGE,
    )

    args = parser.parse_args()

    configure_logging()

    prepare_match(
        input_path=args.input,
        output_root=args.output_root,
    )


if __name__ == "__main__":
    main()
