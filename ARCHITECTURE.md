# AfyaPlus RAG Agent Architecture

## Purpose
This repository implements an enterprise-inspired, document-grounded medical insurance verification and clinical routing agent for AfyaPlus Health.

## Core components

### 1. Privacy-Masking Middleware
- Raw user input is scanned for Kenyan PII patterns:
  - Nairobi-style phone numbers: `+2547XXXXXXXX`, `2547XXXXXXXX`, `07XXXXXXXX`
  - Email addresses
- Detected PII tokens are replaced with placeholders such as `[PHONE_1]` and `[EMAIL_1]`.
- The masked text is used for retrieval and model input only.
- Final outputs re-inject original values safely before presentation.

### 2. Grounded Knowledge Retrieval (RAG)
- Local documents in `knowledge_manual/` are read and chunked with semantic overlap.
- Chunks are indexed locally using a vector store and a lightweight embedding model.
- The agent retrieves the top relevant policy snippets for each prompt.
- Source citations are preserved and exposed in the agent output.

### 3. Agent Orchestration
- The agent uses a prompt template with a system role guardrail.
- It processes masked user text, retrieves grounded context, and optionally invokes helper tools.
- If cloud LLM generation fails, the code falls back to a deterministic reply builder.
- Recent conversation turns are stored in `ConversationMemory` for multi-turn coherence.

### 4. Tooling
- `calculate_metric()` is a defensive, structured calculation helper.
- It supports operations like `dose_volume` and `daily_dose`.
- Tools run with explicit validation and return a JSON-safe payload.

### 5. Audit and Compliance
- Each agent run captures:
  - Masked input
  - Grounded context
  - Source citations
  - Tool usage
  - Audit trail entries
- The output is designed for review and audit, not just freeform response.

## Token and cost management
- The production model is configured with low temperature for determinism.
- The retrieval pipeline limits grounding to a small set of highly relevant policy chunks.
- The agent avoids unnecessary open-ended calls by using pre-built fallback text when the LLM is unavailable.

## Security guardrails
- PII is never passed directly to the model during prompt construction.
- Re-masking is only applied to the final user-facing answer.
- The policy context is the single source of truth for coverage and routing guidance.
- Any ungrounded prediction is accompanied by a default safe routing decision.
