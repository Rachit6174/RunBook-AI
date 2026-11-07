import os
import requests
from dotenv import load_dotenv
from .memory import Hindsight

load_dotenv()

class IncidentResponseAgent:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.memory = Hindsight()
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"

    def handle_incident(self, incident_description):
        print(f"\n[Agent] Analyzing incoming incident: {incident_description}")

        # 1. Recall similar past incidents from memory
        past_memories = []
        try:
            recalled = self.memory.recall(query=incident_description, limit=2)
            if hasattr(recalled, 'results'):
                past_memories = [r.text for r in recalled.results]
        except Exception as e:
            print(f"[Agent] Memory recall warning: {e}")

        # 2. Build prompt with context
        prompt = f"""
You are an expert Autonomous Incident Response Agent.
New Incident Alert: {incident_description}
Relevant Past Incidents: {past_memories}

Provide a concise, step-by-step remediation plan for this incident:
"""

        # 3. Query Groq Qwen Model
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.groq_url, json=payload, headers=headers)
            if response.status_code == 200:
                result_json = response.json()
                remediation_plan = result_json["choices"][0]["message"]["content"]
                
                # 4. Store incident in memory
                self.memory.retain(text=incident_description, metadata={"plan": remediation_plan})
                print("\n[Agent] Remediation Plan:\n" + remediation_plan)
                print("\n[Agent] Incident successfully processed and stored in memory!")
                return remediation_plan
            else:
                print(f"[Agent] Groq API Error: {response.text}")
        except Exception as e:
            print(f"[Agent] Error during execution: {e}")
        finally:
            self.memory.close()

if __name__ == "__main__":
    agent = IncidentResponseAgent()
    agent.handle_incident("High CPU utilization spike detected on production server cluster-01.")
