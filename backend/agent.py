
import os
import base64
import requests

from dotenv import load_dotenv
from .memory import Hindsight

load_dotenv()


class IncidentResponseAgent:

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "qwen/qwen3.8-27b"
        self.memory = Hindsight()
        self.historical_reflection = "No historical reflection available."
        self.reflection_facts = []

        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is missing")

    def handle_incident(
        self,
        incident_description,
        image_inputs=None,
        log_texts=None
    ):
        print("\n[Agent] Analyzing incident:", incident_description)
        self.historical_reflection = "No historical reflection available."
        self.reflection_facts = []

        image_inputs = image_inputs or []
        log_texts = log_texts or []

        try:
            # Retrieve incident evidence and resolutions separately
            past_memories = []

            try:
                evidence_recall = self.memory.recall(
                    query=incident_description,
                    limit=3,
                    tags=["incident_evidence"]
                )

                if hasattr(evidence_recall, "results"):
                    past_memories.extend(
                        "[HISTORICAL INCIDENT] " + getattr(item, "text", str(item))
                        for item in evidence_recall.results
                    )

                resolution_recall = self.memory.recall(
                    query=incident_description,
                    limit=5,
                    tags=["resolution"]
                )

                if hasattr(resolution_recall, "results"):
                    past_memories.extend(
                        "[PREVIOUSLY RECORDED RESOLUTION] " + getattr(item, "text", str(item))
                        for item in resolution_recall.results
                    )

            except Exception as error:
                print("[Agent] Memory recall warning:", error)

            # Generate a historical synthesis using Hindsight Reflect
            historical_reflection = "No historical reflection available."
            reflection_facts = []

            try:
                reflection = self.memory.client.reflect(
                    bank_id=self.memory.bank_id,
                    query=(
                        "Summarize ONLY previously stored historical incident "
                        "records and resolutions in this memory bank. Identify "
                        "recurring technical patterns and previously recorded "
                        "fixes. Do not describe the current incident, current "
                        "approval status, or any current action. Never claim "
                        "that a restart, deployment, rollback, or other action "
                        "is currently authorized, initiated, running, or "
                        "completed. Do not invent dates, metrics, or outcomes. "
                        "Clearly label all outcomes as historical records, "
                        "not verified facts about the current incident."
                    ),
                    budget="low",
                    tags=["incident_evidence", "resolution"],
                    tags_match="any",
                    include_facts=True
                )

                historical_reflection = getattr(
                    reflection, "text", "No historical reflection available."
                )

                based_on = getattr(reflection, "based_on", None)
                memories = getattr(based_on, "memories", []) or []

                reflection_facts = [
                    getattr(item, "text", str(item))
                    for item in memories[:5]
                ]
                self.historical_reflection = historical_reflection
                self.reflection_facts = reflection_facts

                print(
                    f"[Agent] Hindsight Reflect returned "
                    f"{len(reflection_facts)} supporting memories."
                )

            except Exception as error:
                print("[Agent] Hindsight Reflect warning:", error)

            # 2. Combine incident description and log evidence
            evidence_text = "\n\n".join(
                f"Log evidence {index + 1}:\n{log}"
                for index, log in enumerate(log_texts)
            )

            prompt = f"""
You are RunBook AI, a careful production incident response assistant.

INCIDENT:
{incident_description}

UPLOADED LOG EVIDENCE:
{evidence_text if evidence_text else "No log files uploaded."}

HISTORICAL CONTEXT (NOT PROOF):
{past_memories if past_memories else "No relevant past incidents found."}

HINDSIGHT HISTORICAL REFLECTION (NOT PROOF):

{historical_reflection}

SUPPORTING HISTORICAL FACTS:

{chr(10).join(reflection_facts) if reflection_facts else "No supporting historical facts returned."}

IMAGE EVIDENCE:
Analyze attached screenshots for visible errors, timestamps,
metrics, service names and warnings.

MANDATORY ANALYSIS RULES:
- Separate confirmed facts, hypotheses and unknowns.
- Label root cause CONFIRMED, PROBABLE or UNKNOWN.
- Never present a hypothesis as a confirmed root cause.
- CPU and memory snapshots alone cannot establish system health.
- Never use low CPU to rule out a traffic spike or prove I/O wait.
- Do not claim I/O wait without database or system wait metrics.
- Similarity to historical incidents does not prove the same cause.
- Historical resolution records are user-entered, not audited.
- When a relevant historical resolution exists, summarize what was
  previously recorded and explain whether it matches the current evidence.
- Clearly label historical outcomes as previously recorded, not as
  actions performed or fixes verified during the current incident.
- If no relevant historical resolution exists, say so explicitly.
- Never invent past incidents, metrics, configuration values,
  investigation results or completed actions.
- If evidence is insufficient, explicitly say what is missing.

SAFETY:
- Start with read-only investigation.
- Do not terminate connections, change database settings,
  increase pool sizes, restart, fail over, roll back or scale
  without verified evidence and explicit human approval.
- Check database capacity and total connection budgets
  before proposing connection-pool changes.
- Distinguish suggested commands from commands already executed.
- CRITICAL EXECUTION RULE: This agent has no infrastructure execution
  capability. It must NEVER claim that a restart, rollback, scaling,
  termination, deployment or other system-changing action was initiated,
  approved, running or completed.
- A user's statement granting permission is NOT proof of execution.
- Approval requests must remain PENDING until the separate backend
  approval workflow records its decision.
- Always explicitly state: "Execution status: NOT_EXECUTED"
  whenever a system-changing action is requested.
- Never fabricate execution results, approval decisions or service status.

TASK:
1. Summarize the incident and its impact.
2. List confirmed evidence.
3. Give the most likely cause and alternative hypotheses.
4. Give prioritized read-only investigation steps.
5. Suggest mitigations and permanent fixes with approval requirements.
6. Provide verification and monitoring steps.
7. State what evidence is still needed.

OUTPUT:
Write a complete Markdown report in at most 650 tokens.
Use these six short sections:
1. Summary and impact
2. Confirmed evidence
3. Root cause status and hypotheses
4. Read-only investigation (maximum two commands)
5. Mitigation and permanent fix
6. Verification and missing evidence

Use concise bullet points. Do not repeat information.
Finish every section. Never invent findings or omit safety warnings.
"""

            # 3. Construct multimodal message
            content = [
                {
                    "type": "text",
                    "text": prompt
                }
            ]

            for mime_type, image_bytes in image_inputs:
                encoded_image = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{mime_type};base64,"
                            f"{encoded_image}"
                        )
                    }
                })

            # 4. Call Groq
            message_content = (
                content if image_inputs else prompt
            )

            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are RunBook AI, the integrated intelligence "
                            "of an incident-management platform, not a generic "
                            "chatbot. Investigate incidents using only supplied "
                            "evidence and available historical context. "
                            "Distinguish facts, hypotheses and unknowns. "
                            "Prioritize safe read-only investigation. Never "
                            "claim to have accessed infrastructure or executed "
                            "an action unless a connected tool confirms it. "
                            "Require explicit human approval before any "
                            "system-changing action. You have NO infrastructure "
                            "execution tools. Never claim an action was "
                            "initiated, approved, running or completed. User "
                            "permission alone does not execute an action. "
                            "Always report execution_status as NOT_EXECUTED "
                            "unless a real execution tool confirms success. "
                            "Produce actionable, "
                            "concise incident reports."
                        )
                    },
                    {
                        "role": "user",
                        "content": message_content
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 750
            }

            response = requests.post(
                self.groq_url,
                json=payload,
                headers=headers,
                timeout=90
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Groq API error {response.status_code}: "
                    f"{response.text[:1000]}"
                )

            result = response.json()

            remediation_plan = (
                result["choices"][0]["message"]["content"]
            )

            if not remediation_plan:
                raise RuntimeError(
                    "Groq returned an empty remediation plan."
                )

            # Store original evidence only, not AI-generated conclusions
            try:
                self.memory.retain(
                    text=(
                        f"Incident description: {incident_description}\n"
                        f"Original log evidence: {evidence_text or 'None'}"
                    ),
                    metadata={"record_type": "incident_evidence"},
                    tags=["incident_evidence"]
                )
            except Exception as error:
                print("[Agent] Memory retain warning:", error)

            print("\n[Agent] Remediation plan generated.")
            return remediation_plan

        finally:
            self.memory.close()


if __name__ == "__main__":
    agent = IncidentResponseAgent()

    try:
        agent.handle_incident(
            "High CPU utilization spike detected on production server."
        )
    finally:
        pass
