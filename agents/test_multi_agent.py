
import asyncio
import json

from agents.config import (
    FSI_TEST_RUN_ID,
    FSI_TEST_AS_OF_SECOND,
)
from agents.workflow import run_fsi_workflow


async def main():
    result = await run_fsi_workflow(
        run_id=FSI_TEST_RUN_ID,
        as_of_second=FSI_TEST_AS_OF_SECOND,
        fan_level="beginner",
        preferred_team="BLU",
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
