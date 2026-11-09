from backend.memory import Hindsight


def test_hindsight_retain_and_recall():
    memory = Hindsight()

    try:
        incident = (
            "Payment API database connection timeout caused by "
            "an exhausted connection pool."
        )

        memory.retain(
            text=incident,
            metadata={
                "test": "true",
                "service": "Payment API"
            }
        )

        result = memory.recall(
            query="Payment API database connection timeout",
            limit=3
        )

        assert hasattr(result, "results")
        assert isinstance(result.results, list)

    finally:
        memory.close()
