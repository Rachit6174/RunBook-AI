from backend.memory import Hindsight


def test_resolution_tracking():
    memory = Hindsight()

    try:
        memory.track_resolution(
            incident_id="INC-TEST-001",
            incident="Authentication API database timeout",
            status="resolved",
            resolution_details=(
                "Corrected database connection pool configuration."
            )
        )

    finally:
        memory.close()
