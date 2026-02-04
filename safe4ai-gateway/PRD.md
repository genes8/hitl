# safe4ai-gateway — PRD (v0.1)

## 1) One-liner
On-prem / self-hostable **AI Gateway** that proxies LLM calls and enforces **security + data policies**, with optional **Secure RAG** over PostgreSQL/pgvector.

## 2) Primary user + buyer
- Primary users: engineering teams integrating LLMs; security/IT enforcing policy.
- Buyer: CTO/CISO/Head of Engineering at agencies / mid-market product teams.

## 3) Problem
Teams adopt LLM APIs fast and leak risk:
- Secrets/API keys accidentally passed to models/logs.
- PII or confidential docs exfiltration risk.
- No consistent policy enforcement across apps.

## 4) Goals (MVP)
1. **Drop-in gateway** compatible with common LLM API shapes.
2. **Policy engine** that can BLOCK/ALLOW and explain why.
3. **Redaction/detection** for secrets and high-risk patterns.
4. **Audit logs** (who/what/when/decision) in PostgreSQL.
5. Optional: **Secure RAG** (retrieve from approved corp docs) with permission-aware hooks.

## 5) Non-goals (v0.1)
- Full multi-tenant enterprise RBAC portal.
- Complex billing/usage-based invoicing.
- Perfect DLP coverage (we ship iterative detectors + roadmap).

## 6) Core features
### 6.1 Proxy / Gateway
- HTTP gateway that accepts requests and forwards to:
  - Local model (Ollama or llama.cpp) OR
  - Cloud providers (OpenAI/Azure/etc.) via connectors.
- Normalization layer: canonical internal request format.

### 6.2 Policy engine (first policies)
- **SECRET_DETECTION**: detect API keys/tokens/private keys → default action: **BLOCK**.
- **PII_DETECTION (basic)**: emails, phone numbers, SSN-like patterns → action: configurable (BLOCK or WARN).
- **ALLOWLIST / DENYLIST** for model/provider, domains, and tool/function calls (later).
- Decisions are explainable: rule hit + matched snippet hashes (no raw secrets stored).

### 6.3 Secure RAG (optional module)
- Document ingestion into PostgreSQL + pgvector.
- Retrieval pipeline:
  - permission filter hook (v0.1 = stub + example)
  - top-k retrieval + citations
- Policy: block sending raw documents outside allowed provider.

### 6.4 Observability + audit
- Structured logs
- DB audit table: request metadata, policy decision, latency, provider
- Minimal admin endpoints (health, metrics)

## 7) API surface (v0.1)
- `POST /v1/chat/completions` (OpenAI-like shape) → proxy + policy
- `POST /v1/embeddings` → proxy + policy
- `GET /healthz`
- `GET /readyz`
- `GET /metrics` (optional)

RAG module:
- `POST /rag/ingest` (MVP; can be disabled)
- `POST /rag/query`

## 8) Data model (Postgres)
- `audit_requests` (id, ts, caller, model, provider, decision, reason_code, latency_ms, token_counts, hashes)
- `documents` (id, source, metadata, acl tags)
- `document_chunks` (doc_id, chunk_id, embedding vector, text hash)

## 9) Security / compliance posture
- Positioning: **HIPAA-ready (roadmap)**, not “HIPAA compliant”.
- Never store raw secrets; store hashes + rule IDs.
- Configurable retention.

## 10) Tech stack (implementation default)
- Backend: **FastAPI**
- DB: **PostgreSQL + pgvector**
- Frontend (later admin UI): **React + TypeScript**, TanStack

## 11) Milestones
### M0 (1–2 days): skeleton
- Docker compose: gateway + postgres (+ pgvector)
- health endpoints + config loading

### M1 (3–5 days): proxy + audit
- proxy to one provider (OpenAI-compatible)
- DB audit logs

### M2 (5–7 days): policy block secrets
- detectors + BLOCK responses
- explainable reason codes

### M3 (1–2 weeks): optional Secure RAG
- ingestion + retrieval + citations

## 12) Definition of Done for PR #1
- Repo boots via `docker compose up`
- Gateway serves `/healthz`
- Postgres has migrations + audit table
- README: local run + env vars
