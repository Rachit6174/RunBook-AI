import os
from dotenv import load_dotenv
from backend.memory import Hindsight

load_dotenv()

bank_id = os.getenv("HINDSIGHT_BANK_ID", "test-bank-123")

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.ai"),
    api_key=os.getenv("HINDSIGHT_API_KEY", "test-key-123")
)

try:
    # Store a sample incident
    client.retain(
        bank_id=bank_id,
        content=(
            "Incident INC-001: Payment API experienced a database "
            "connection timeout. The connection pool was exhausted. "
            "The confirmed resolution was correcting the database "
            "connection pool configuration."
        ),
        context="RunBook AI incident memory integration test",
        metadata={"incident_id": "INC-001", "service": "Payment API"}
    )

    print("SUCCESS: Incident stored in Hindsight!")

    # Search for a similar incident
    result = client.recall(
        bank_id=bank_id,
        query="Payment API database connection timeout and exhausted connection pool"
    )

    print("\nSimilar incidents found:")

    if result.results:
        for memory in result.results:
            print("-", memory.text)
    else:
        print("No matching memories returned yet.")

finally:
    client.close()
