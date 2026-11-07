from backend.memory import (
    retain_incident,
    recall_similar_incidents,
    retain_resolution
)

incident = {
    "incident_id": "INC-MODULE-001",
    "service": "Authentication API",
    "error": "Database connection timeout",
    "description": (
        "The authentication service could not connect "
        "to its database during user login."
    )
}

try:
    # 1. Store incident
    print("1. Storing incident...")
    print(retain_incident(incident))

    # 2. Retrieve similar incidents
    print("\n2. Searching Hindsight memory...")
    memories = recall_similar_incidents(
        "Authentication API database connection timeout during login"
    )

    if memories:
        for memory in memories:
            print("-", memory)
    else:
        print("No matching memories returned.")

    # 3. Store resolution outcome
    print("\n3. Storing resolution...")
    print(
        retain_resolution(
            incident_id="INC-MODULE-001",
            service="Authentication API",
            resolution="Corrected database connection pool configuration",
            successful=True,
            details="Login requests succeeded after the configuration change."
        )
    )

    print("\nMODULE TEST COMPLETED!")

except Exception as error:
    print("\nMODULE TEST FAILED:", error)
