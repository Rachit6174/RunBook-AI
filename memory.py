import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()


def _get_client():
    """Create a Hindsight client using environment configuration."""
    base_url = os.getenv("HINDSIGHT_BASE_URL")
    api_key = os.getenv("HINDSIGHT_API_KEY")

    if not base_url or not api_key:
        raise ValueError("Hindsight configuration is missing from .env")

    return Hindsight(
        base_url=base_url,
        api_key=api_key
    )


def _get_bank_id():
    bank_id = os.getenv("HINDSIGHT_BANK_ID")

    if not bank_id:
        raise ValueError("HINDSIGHT_BANK_ID is missing from .env")

    return bank_id


def retain_incident(incident):
    """Store a new software incident in Hindsight."""
    client = _get_client()

    try:
        bank_id = _get_bank_id()

        content = f"""
        Incident ID: {incident.get('incident_id', 'Unknown')}
        Service: {incident.get('service', 'Unknown')}
        Error: {incident.get('error', 'Not specified')}
        Description: {incident.get('description', 'Not specified')}
        """

        client.retain(
            bank_id=bank_id,
            content=content,
            context="RunBook AI software incident",
            metadata={
                "incident_id": str(incident.get("incident_id", "unknown")),
                "service": str(incident.get("service", "unknown")),
                "record_type": "incident"
            }
        )

        return {"success": True, "message": "Incident stored successfully"}

    finally:
        client.close()


def recall_similar_incidents(query, max_tokens=2048):
    """Find relevant previous incidents using Hindsight."""
    client = _get_client()

    try:
        result = client.recall(
            bank_id=_get_bank_id(),
            query=query,
            max_tokens=max_tokens
        )

        return [memory.text for memory in result.results]

    finally:
        client.close()


def retain_resolution(
    incident_id,
    service,
    resolution,
    successful,
    details=""
):
    """Store the outcome of an incident resolution."""
    client = _get_client()

    try:
        status = "SUCCESSFUL" if successful else "UNSUCCESSFUL"

        content = f"""
        Resolution for Incident: {incident_id}
        Service: {service}
        Resolution attempted: {resolution}
        Outcome: {status}
        Additional details: {details}
        """

        client.retain(
            bank_id=_get_bank_id(),
            content=content,
            context="RunBook AI incident resolution feedback",
            metadata={
                "incident_id": str(incident_id),
                "service": str(service),
                "record_type": "resolution",
                "successful": str(successful)
            }
        )

        return {"success": True, "message": "Resolution stored successfully"}

    finally:
        client.close()
