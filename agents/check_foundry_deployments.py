
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

from agents.config import (
    FOUNDRY_PROJECT_ENDPOINT,
    FOUNDRY_MODEL,
)


def main():
    print("[FOUNDRY] Checking project deployments...")
    print(f"Configured model: {FOUNDRY_MODEL}")

    credential = AzureCliCredential()

    try:
        client = AIProjectClient(
            endpoint=FOUNDRY_PROJECT_ENDPOINT,
            credential=credential,
        )

        deployments = list(client.deployments.list())

        if not deployments:
            print("[WARNING] No model deployments found.")
            return

        print("\n=== AVAILABLE DEPLOYMENTS ===")

        for deployment in deployments:
            print(f"Deployment name: {deployment.name}")
            print(f"Details: {deployment}")
            print("-" * 50)

        names = [deployment.name for deployment in deployments]

        print("\n=== CONFIGURATION CHECK ===")

        if FOUNDRY_MODEL in names:
            print("[OK] Configured model exists in this project.")
        else:
            print("[ERROR] Configured model was not found.")
            print(f"Your .env has: {FOUNDRY_MODEL}")
            print(f"Available deployments: {names}")

    finally:
        credential.close()


if __name__ == "__main__":
    main()
