
import os
import requests
from dotenv import load_dotenv

from .memory import Hindsight

load_dotenv()


class IncidentResponseAgent:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

        # Hindsight is optional for the demo.
        self.memory = None
        try:
            self.memory = Hindsight()
            print("[Agent] Hindsight connected.")
        except Exception as e:
            print(f"[Agent] Hindsight unavailable: {e}")

    def handle_incident(self, incident_description):
        print(f"[Agent] Analyzing: {incident_description}")

        past_memories = []

        if self.memory:
            try:
                recalled = self.memory.recall(
                    query=incident_description, limit=2
                )
                if hasattr(recalled, "results"):
                    past_memories = [r.text for r in recalled.results]
            except Exception as e:
                print(f"[Agent] Recall warning: {e}")

        prompt = f"""
You are an expert incident response assistant.
Analyze this incident: {incident_description}

Relevant past incidents: {past_memories}

Give a concise, practical remediation plan.
"""

        remediation_plan = None

        if self.groq_api_key and self.groq_api_key != "your_groq_api_key":
            try:
                response = requests.post(
                    self.groq_url,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen/qwen3.8-27b",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3
                    },
                    timeout=30
                )

                response.raise_for_status()
                remediation_plan = response.json()["choices"][0]["message"]["content"]

            except Exception as e:
                print(f"[Agent] Groq warning: {e}")

        # Fallback so the demo can still accept incidents.
        if not remediation_plan:
            remediation_plan = (
                "Demo remediation plan:\n"
                "1. Check API server health and response-time metrics.\n"
                "2. Inspect application logs for slow requests.\n"
                "3. Check database query performance and resource usage.\n"
                "4. Apply the appropriate fix and retest the API.\n"
                "5. Monitor response times after the fix."
            )

        if self.memory:
            try:
                self.memory.retain(
                    text=incident_description,
                    metadata={"plan": remediation_plan}
                )
            except Exception as e:
                print(f"[Agent] Memory storage warning: {e}")

        return remediation_plan

    def close(self):
        if self.memory:
            try:
                self.memory.close()
            except Exception as e:
                print(f"[Agent] Memory close warning: {e}")
