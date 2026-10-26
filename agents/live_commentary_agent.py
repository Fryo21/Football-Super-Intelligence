
"""Connect to the existing FSI Commentary Agent in Foundry."""

import os

from azure.identity import AzureCliCredential
from agent_framework.foundry import FoundryAgent
from agents.config import FOUNDRY_PROJECT_ENDPOINT


def create_live_commentary_agent():
    return FoundryAgent(
        project_endpoint=FOUNDRY_PROJECT_ENDPOINT,
        agent_name=os.getenv(
            "FSI_COMMENTARY_AGENT_NAME",
            "fsi-commentary-analysis",
        ),
        agent_version=os.getenv(
            "FSI_COMMENTARY_AGENT_VERSION",
            "1",
        ),
        credential=AzureCliCredential(),
    )
