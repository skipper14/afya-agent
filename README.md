# AfyaPlus Triage Engine

## Overview
This project implements a production-style Python inference engine for the AfyaPlus triage workflow. It uses a cloud-first pathway with OpenAI and a local fallback pathway with Ollama so the system can continue operating when network conditions degrade.

## Architecture
- Cloud pathway: OpenAI GPT-4o-mini with strict JSON mode and a 4.0s timeout.
- Local pathway: Ollama running `llama3.2` for offline fallback.
- Grounded RAG: local policy documents are chunked and indexed as a retriever to provide policy context for answers.
- Privacy Middleware: Kenyan phone numbers and email addresses are masked before model processing and restored only in the final approved output.
- Tool calling: a safe calculator function is available for structured medication and dosing computations.
- Message memory: the agent retains recent conversation history for stateful, multi-turn dialog.

## Key additions for this repository
- `ARCHITECTURE.md`: design choices, compliance guardrails, token management, and tool orchestration.
- `GIT_FLOW.md`: branch isolation, semantic commit guidance, PR review checklist, and release validation.
- `tests/test_afya_agent.py`: regression coverage for privacy masking, tool execution, citation capture, and audit trail generation.

## Compliance and governance
- Sensitive personal identifiers are masked prior to model input, complying with Kenya Data Protection Act (2019) principles.
- The agent is grounded in documented policy sources, with source citations captured for auditability.
- A clear audit trail is generated for each agent invocation, including retrieval sources and tool usage.

## How to run
```bash
python3 afya_agent.py "I have a medication refill request"
```

## Repository workflow
- Create feature branches from `main` using descriptive names such as `feat/rag-agent-system`.
- Final code updates should be delivered through a pull request merged into `main`; this repository uses `feat-rag-agent-system` as the example feature branch for the current work.
- Use semantic commit messages: `feat: add policy-guided RAG retriever`, `fix: enforce PII masking`, `docs: add architecture and git flow guidance`.
- Open PRs with a checklist that includes tests, documentation, and security review.
- Keep the main branch deployable at all times.

## Prompt Engineering Iterations
### Variant 1: Baseline
- Simple instructional prompt.
- Helpful, but lacked strong guardrails.

### Variant 2: Structured Output Focus
- Explicitly requested a JSON object and blocked markdown.
- Improved schema adherence.

### Variant 3: Guardrailed Production Prompt
- Added role-based identity.
- Forced internal reasoning steps without revealing the chain of thought.
- Added defensive rules to eliminate conversational fluff and unsupported medical claims.

## Why the Guardrails Matter
The AfyaPlus backend requires machine-readable input. Without strict rules, the model may add prose, make unsupported medical claims, or return invalid wrappers. The final prompt prevents these failure modes by restricting output to a single valid JSON object.

## Baseline Performance Comparison

| Path | Tool | Approx. latency | Notes |
| --- | --- | ---: | --- |
| Cloud | OpenAI GPT-4o-mini | ~1-3s when key is valid | Fast but depends on network and authentication |
| Local | Ollama + llama3.2 | ~8-12s | Reliable fallback, but slower and less deterministic |

## How to Run
```bash
python3 app.py "I have had severe chest pain for 20 minutes and I feel short of breath."
```

## Sample Outputs
1. Cloud success path: valid JSON returned from the OpenAI route.
2. Cloud failure path: the script prints a cloud error and falls back to Ollama.
3. Local fallback path: Ollama returns a valid JSON object for the same message.
