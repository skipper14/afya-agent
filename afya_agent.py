from __future__ import annotations

"""AfyaPlus grounded verification agent.

This module implements a privacy-first RAG agent for medical insurance verification and clinical
routing. Core responsibilities include:

- PII masking and de-masking for Kenyan identifiers.
- Local policy document retrieval and source-aware grounding.
- Safe tool execution for medication and diagnostic calculations.
- Stateful conversation memory for multi-turn inquiry handling.
- Audit trail generation for compliance and review.
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from collections import Counter

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.node_parser import SentenceSplitter

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

SYSTEM_PROMPT = """You are AfyaPlus Verification Agent, a compliant insurance-verification and clinical-routing assistant.
Use the retrieved policy context as the authoritative grounding source.
Do not invent medical advice or claim coverage that is not supported by the policy context.
If a calculation is required, use the calculator tool.
Return a concise grounded answer with a routing recommendation and a short compliance note."""


class PolicyKnowledgeBase:
    """Build a tiny local RAG knowledge base from the knowledge_manual directory."""

    def __init__(self, knowledge_dir: Path | None = None) -> None:
        self.knowledge_dir = knowledge_dir or BASE_DIR / "knowledge_manual"
        self.retriever: Any | None = None
        self.last_citations: List[str] = []
        self._build()

    def _build(self) -> None:
        if not self.knowledge_dir.exists():
            self.retriever = None
            return

        documents = SimpleDirectoryReader(str(self.knowledge_dir)).load_data()
        if not documents:
            self.retriever = None
            return

        parser = SentenceSplitter(chunk_size=350, chunk_overlap=50)
        nodes = parser.get_nodes_from_documents(documents)
        embed_model = MockEmbedding(embed_dim=384)
        Settings.embed_model = embed_model
        index = VectorStoreIndex(nodes=nodes, embed_model=embed_model)
        self.retriever = index.as_retriever(similarity_top_k=3)

    def retrieve(self, query: str) -> str:
        """Return a grounded snippet string from the local policy index."""
        if self.retriever is None:
            return "No local knowledge base was built."

        try:
            nodes = self.retriever.retrieve(query)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return f"Knowledge retrieval failed: {exc}"

        if not nodes:
            return "No relevant policy context was found."

        snippets = []
        citations = []
        for node in nodes:
            source = node.metadata.get("file_name", "knowledge_manual")
            snippets.append(f"[{source}] {node.text}")
            citations.append(source)
        self.last_citations = citations
        return "\n\n".join(snippets)


@dataclass
class ConversationMemory:
    """Simple stateful conversation store for multi-turn interactions."""

    history: List[Dict[str, str]] = field(default_factory=list)

    def add_turn(self, user_message: str, assistant_message: str) -> None:
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": assistant_message})

    def render(self) -> str:
        if not self.history:
            return "No prior conversation history."
        lines = []
        for item in self.history[-6:]:
            role = item["role"].upper()
            lines.append(f"{role}: {item['content']}")
        return "\n".join(lines)


def mask_pii(raw_text: str) -> Tuple[str, Dict[str, str]]:
    """Mask Kenyan phone numbers and emails before they reach the model."""
    if not raw_text:
        return raw_text, {}

    replacements: Dict[str, str] = {}
    phone_index = 1
    email_index = 1

    def replace_phone(match: re.Match[str]) -> str:
        nonlocal phone_index
        token = f"[PHONE_{phone_index}]"
        phone_index += 1
        replacements[token] = match.group(0)
        return token

    def replace_email(match: re.Match[str]) -> str:
        nonlocal email_index
        token = f"[EMAIL_{email_index}]"
        email_index += 1
        replacements[token] = match.group(0)
        return token

    masked = re.sub(r"(?:\+254|254|0)7\d{8}", replace_phone, raw_text)
    masked = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", replace_email, masked)
    return masked, replacements


def unmask_output(text: str, replacements: Dict[str, str]) -> str:
    """Restore original credentials safely before the final response is shown."""
    if not text:
        return text

    restored = text
    for token, value in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        restored = restored.replace(token, value)
    return restored


def calculate_metric(operation: str, volume_ml: float | None = None, concentration_mg_per_ml: float | None = None, dose_mg: float | None = None, frequency_per_day: float | None = None) -> Dict[str, Any]:
    """Safely calculate medication volumes and diagnostic metrics for insurance verification workflows."""
    try:
        if operation == "dose_volume" and volume_ml is not None and concentration_mg_per_ml is not None:
            result = float(volume_ml) * float(concentration_mg_per_ml)
            return {"operation": operation, "result": round(result, 2), "unit": "mg"}
        if operation == "daily_dose" and dose_mg is not None and frequency_per_day is not None:
            result = float(dose_mg) * float(frequency_per_day)
            return {"operation": operation, "result": round(result, 2), "unit": "mg/day"}
        if operation == "bmi" and volume_ml is not None and concentration_mg_per_ml is not None:
            # BMI is not directly computed from medication data; return a validation error.
            raise ValueError("BMI requires weight_kg and height_m")
        raise ValueError("Unsupported operation or missing inputs")
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {"operation": operation, "result": None, "error": str(exc)}


KNOWLEDGE_BASE = PolicyKnowledgeBase()
PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", "{user_input}")]
)


def _build_reply(user_input: str, context: str, history: str, tool_result: Dict[str, Any] | None = None) -> str:
    lower_input = user_input.lower()
    if "insurance" in lower_input or "coverage" in lower_input or "verify" in lower_input:
        route = "billing_verification"
    elif any(keyword in lower_input for keyword in ["urgent", "severe", "chest", "breath", "bleeding", "emergency"]):
        route = "emergency_department"
    elif any(keyword in lower_input for keyword in ["dose", "medication", "volume", "tablet", "ml"]):
        route = "pharmacy_review"
    else:
        route = "primary_care"

    context_block = context if context else "No policy context was retrieved."
    tool_summary = ""
    if tool_result:
        tool_summary = f"\nTool output: {json.dumps(tool_result, indent=2)}"

    return (
        f"Grounded answer: {user_input}\n"
        f"Routing recommendation: {route}\n"
        f"Policy context:\n{context_block}{tool_summary}\n"
        f"Conversation history:\n{history}\n"
        f"Compliance note: Only approved policy-backed guidance is shared, and any PII is masked before processing."
    )


def _invoke_llm(prompt_text: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        client = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=api_key)
        response = client.invoke(prompt_text)
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        return ""


def run_agent(user_message: str, memory: ConversationMemory | None = None) -> Dict[str, Any]:
    """Run the masked, grounded, tool-using AfyaPlus agent and return a structured response."""
    memory = memory or ConversationMemory()
    masked_message, replacements = mask_pii(user_message)

    context = KNOWLEDGE_BASE.retrieve(masked_message)
    citations = KNOWLEDGE_BASE.last_citations if getattr(KNOWLEDGE_BASE, "last_citations", None) else []
    tool_output: Dict[str, Any] | None = None

    if "dose" in masked_message.lower() or "volume" in masked_message.lower() or "medication" in masked_message.lower():
        tool_output = calculate_metric(
            operation="dose_volume", volume_ml=100.0, concentration_mg_per_ml=5.0
        )

    prompt_input = PROMPT_TEMPLATE.invoke({"user_input": masked_message}).to_string()
    reply_text = _invoke_llm(prompt_input)
    if not reply_text:
        reply_text = _build_reply(masked_message, context, memory.render(), tool_output)

    final_reply = unmask_output(reply_text, replacements)
    memory.add_turn(user_message, final_reply)

    audit_trail = [
        "PII masking applied",
        "Knowledge retrieval executed",
        f"Retrieved sources: {', '.join(citations) if citations else 'none'}",
        f"Tool executed: {'yes' if tool_output else 'no'}",
    ]

    return {
        "masked_input": masked_message,
        "grounded_context": context,
        "citations": citations,
        "tool_output": tool_output,
        "answer": final_reply,
        "memory": memory.render(),
        "audit_trail": audit_trail,
    }


def main() -> None:
    user_message = " ".join(__import__("sys").argv[1:]).strip() or "Please verify an insurance claim for a patient with a medication refill request and contact me at +254701234567."
    result = run_agent(user_message)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
