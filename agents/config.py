
import os
from pathlib import Path

from dotenv import load_dotenv

# Find project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Check whether .env exists
load_dotenv(dotenv_path=ENV_FILE, override=False)

# Load variables from .env.
# Existing Azure App Service environment variables take precedence.
load_dotenv(dotenv_path=ENV_FILE, override=False)


def required_env(name: str) -> str:
    value = os.getenv(name)

    if not value or not value.strip():
        raise RuntimeError(
            f"Missing environment variable: {name}. "
            f"Check {ENV_FILE}"
        )

    return value.strip()


# Microsoft Fabric
FSI_KUSTO_URI = required_env("FSI_KUSTO_URI")
FSI_KUSTO_DATABASE = os.getenv(
    "FSI_KUSTO_DATABASE", "fsi_db"
)

# Microsoft Foundry
FOUNDRY_PROJECT_ENDPOINT = required_env(
    "FOUNDRY_PROJECT_ENDPOINT"
)
FOUNDRY_MODEL = required_env("FOUNDRY_MODEL")

# Testing
FSI_TEST_RUN_ID = required_env("FSI_TEST_RUN_ID")
FSI_TEST_AS_OF_SECOND = float(
    os.getenv("FSI_TEST_AS_OF_SECOND", "5400")
)
