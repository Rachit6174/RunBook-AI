import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

client = Hindsight(
    base_url=os.environ["HINDSIGHT_BASE_URL"],
    api_key=os.environ["HINDSIGHT_API_KEY"]
)

try:
    bank = client.create_bank(
        bank_id=os.environ["HINDSIGHT_BANK_ID"],
        name="RunBook AI Incident Memory",
        background="Stores software incidents, troubleshooting experiences, and confirmed resolutions for RunBook AI."
    )
    print("SUCCESS: Hindsight memory bank is ready!")
    print("Bank ID:", bank.bank_id)

except Exception as e:
    print("HINDSIGHT ERROR:", e)

finally:
    client.close()
