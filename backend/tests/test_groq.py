import os
import requests
from dotenv import load_dotenv

load_dotenv()


def test_groq_api_connection():
    api_key = os.getenv("GROQ_API_KEY")

    assert api_key, "GROQ_API_KEY is missing from .env"

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly GROQ_OK"
            }
        ],
        "temperature": 0
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    assert response.status_code == 200, (
        f"Groq API returned {response.status_code}: {response.text}"
    )

    data = response.json()

    assert data["choices"], "Groq returned no choices"
    assert data["choices"][0]["message"]["content"], (
        "Groq returned an empty response"
    )
