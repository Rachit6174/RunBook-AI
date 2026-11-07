import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

def test_http_connection():
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen3.8-27b",
        "messages": [
            {"role": "user", "content": "Say 'Groq connection successful!' and nothing else."}
        ]
    }
    
    try:
        print("Sending direct HTTP request to Groq API...")
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Response Body:", response.text)
    except Exception as e:
        print(f"HTTP request failed: {e}")

if __name__ == "__main__":
    test_http_connection()
    