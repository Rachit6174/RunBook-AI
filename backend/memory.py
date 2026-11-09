import os
from types import SimpleNamespace
from dotenv import load_dotenv
from hindsight_client import Hindsight as HindsightClient

load_dotenv()


class Hindsight:
    def __init__(self):
        api_key = os.getenv("HINDSIGHT_API_KEY")
        base_url = os.getenv(
            "HINDSIGHT_BASE_URL",
            "https://api.hindsight.vectorize.io"
        )
        self.bank_id = os.getenv("HINDSIGHT_BANK_ID", "recallOPS")

        if not api_key:
            raise ValueError("HINDSIGHT_API_KEY is missing")

        self.client = HindsightClient(
            base_url=base_url,
            api_key=api_key
        )

        self.client.create_bank(
            bank_id=self.bank_id,
            name="RunBook AI Incident Memory"
        )

    def retain(self, text, metadata=None, tags=None):
        kwargs = {
            "bank_id": self.bank_id,
            "content": text,
            "metadata": metadata or {}
        }
        if tags:
            kwargs["tags"] = tags
        return self.client.retain(**kwargs)

    def recall(self, query, limit=2, tags=None):
        kwargs = {
            "bank_id": self.bank_id,
            "query": query
        }
        if tags:
            kwargs["tags"] = tags
            kwargs["tags_match"] = "any_strict"

        result = self.client.recall(**kwargs)
        return SimpleNamespace(results=result.results[:limit])

    def track_resolution(self, incident_id, incident, status, resolution_details):
        if status not in ("resolved", "failed"):
            raise ValueError("Status must be 'resolved' or 'failed'")
        return self.retain(
            text=(
                f"User-recorded resolution for incident {incident_id}: "
                f"{incident}. Status: {status}. "
                f"Resolution details: {resolution_details}"
            ),
            metadata={
                "incident_id": str(incident_id),
                "resolution_status": str(status),
                "resolution_details": str(resolution_details),
                "record_type": "resolution"
            },
            tags=["resolution"]
        )

    def close(self):
        self.client.close()
