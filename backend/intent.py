import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class IntentClassifier:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "qwen/qwen3.8-27b"

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is missing")

    def classify(self, message, conversation_context=""):
        prompt = f"""
You are RunBook AI, an intelligent IT operations agent.

Understand the user's actual intent. Do not assume every message is
a software incident.

CLASSIFY INTO EXACTLY ONE CATEGORY:

1. incident:
A real or suspected IT failure, outage, error, alert, abnormal
system behaviour, performance degradation, or operational issue.

2. technical_question:
The user wants technical explanations, programming help,
architecture advice, debugging guidance, or IT knowledge.
There is no reported active incident.

3. non_technical:
General conversation, greetings, everyday questions, or topics
unrelated to IT, software engineering, or operations.

4. clarification:
The message is too vague to understand reliably. Ask one
specific question rather than guessing.

5. action_request:
The user explicitly asks you to perform an operation that changes
a system, such as restarting a service, deleting data, deploying
code, changing configuration, or modifying a database.

IMPORTANT DISTINCTIONS:
- "How do I restart a server?" is technical_question.
- "Restart my production server now" is action_request.
- "Our production server is down" is incident.
- "Our production server is down. Restart it" is incident,
  with action_requested=true.
- "Hello, how are you?" is non_technical.
- "Explain HTTP 503" is technical_question.
- "The text is not good" is clarification unless prior context
  clearly identifies the technical issue.

SAFETY:
- Never claim to have accessed a real system.
- Never claim to have executed an operation.
- Never invent logs, metrics, evidence, or root causes.
- System-changing actions always require explicit human approval.
- Read-only explanations and analysis do not require approval.
- Preserve the user's original meaning.

CONTEXT:
{conversation_context or "No previous conversation context."}

USER MESSAGE:
{message}

Return ONLY valid JSON:
{{
  "intent": "incident",
  "incident_description": "",
  "answer": "",
  "clarification": "",
  "action_requested": false,
  "proposed_action": "",
  "risk_level": "low"
}}

For action_request, describe the requested action but do not execute it.
For incident, preserve the original incident description.
For technical_question and non_technical, provide a useful answer.
For clarification, ask one concise question.
risk_level must be low, medium, high, or unknown.
"""

        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 650,
                "response_format": {"type": "json_object"}
            },
            timeout=45
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Intent classification failed ({response.status_code}): "
                f"{response.text[:500]}"
            )

        content = response.json()["choices"][0]["message"]["content"]
        result = json.loads(content)

        allowed = {
            "incident",
            "technical_question",
            "non_technical",
            "clarification",
            "action_request"
        }

        intent = result.get("intent")
        if intent not in allowed:
            raise ValueError(f"Invalid classifier intent: {intent}")

        risk = str(result.get("risk_level", "unknown")).lower()
        if risk not in {"low", "medium", "high", "unknown"}:
            risk = "unknown"

        return {
            "intent": intent,
            "incident_description": str(
                result.get("incident_description", "")
            ).strip(),
            "answer": str(result.get("answer", "")).strip(),
            "clarification": str(
                result.get("clarification", "")
            ).strip(),
            "action_requested": bool(
                result.get("action_requested", False)
            ),
            "proposed_action": str(
                result.get("proposed_action", "")
            ).strip(),
            "risk_level": risk
        }
