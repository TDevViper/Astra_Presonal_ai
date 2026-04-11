<div align="center">

```
█████╗ ███████╗████████╗██████╗  █████╗
██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗
███████║███████╗   ██║   ██████╔╝███████║
██╔══██║╚════██║   ██║   ██╔══██╗██╔══██║
██║  ██║███████║   ██║   ██║  ██║██║  ██║
╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
```

**Local Personal AI System · Pipeline Architecture · 100% Private**

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![CI](https://github.com/TDevViper/Astra_Presonal_ai/actions/workflows/ci.yml/badge.svg)](https://github.com/TDevViper/Astra_Presonal_ai/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)](https://docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat-square)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Built by Arnav Yadav · Runs 100% locally · No cloud · No data leaves your device*

</div>

---

## What is ASTRA?

ASTRA is a personal AI system that runs entirely on your machine. It combines a modular pipeline architecture, hybrid memory, real-time vision, and voice — all without sending a single byte to an external server.

This is not a chatbot wrapper. It is a production-quality local AI backend with:

- A **modular pipeline registry** where every handler is an independent, testable class
- A **hybrid memory system** — episodic, semantic (vector), and structured fact storage with per-user isolation
- A **ReAct agent loop** with async parallel tool execution via `asyncio.gather`
- A **TruthGuard** hallucination filter on every response
- A **self-improvement loop** with a quality gate — 3 unique sessions must approve a response before it enters the fine-tune dataset
- **Full async FastAPI** backend — blocking LLM calls wrapped in `asyncio.to_thread`, nothing blocks the event loop
- **Session-scoped caching** — zero cross-user response leakage, cache keyed to JWT sub not API key
- **Signed approval tokens** for all destructive tool operations (HMAC-SHA256, 60s TTL)
- **RBAC permission matrix** — owner > admin > user > guest, enforced on every route
- **113 passing tests**, ruff lint clean, CI on every push

---

## Architecture

```
User Request
│
▼
[FastAPI — main.py]
JWT auth · Rate limiter (per-user, Redis-backed) · CORS · Request ID · OTel tracing
│
▼
[PipelineRegistry — core/pipeline/]
Handlers run in order. First match wins.
┌──────────────────────┐
│ ModeSwitchHandler    │  detect focus / creative / precise mode
│ CacheHandler         │  session-scoped SHA-256 cache (Redis / local)
│ ChainHandler         │  multi-step query decomposition
│ QuickToolHandler     │  time, math, calendar — no LLM needed
│ IntentShortcutHandler│  known-pattern fast exits
│ MemoryHandler        │  episodic + semantic recall
│ WebSearchHandler     │  DuckDuckGo with citation extraction
│ AgentHandler         │  ReAct loop with parallel tool calls
│ LLMHandler           │  Ollama via pluggable LLMBackend interface
└──────────────────────┘
│
▼
[RequestContext]           per-request, immutable, no shared state
[MemoryTransaction]        batch all writes, commit once at end
[ObservabilityStore]       async writes, non-blocking
```

### Key architectural properties

- **No shared mutable state** — `Brain` holds no conversation history. History is loaded fresh per request from `memory_db` and written back at the end.
- **Pluggable LLM backend** — `core/llm_backend.py` defines `LLMBackend(ABC)`. `OllamaBackend` and `StubBackend` (for testing) are included. Adding OpenAI or Anthropic means implementing 4 methods.
- **Pipeline is open for extension, closed for modification** — adding a new capability means adding a `Handler` subclass and registering it. `brain.py` is never edited.
- **Single entry point** — `main.py` is the only server.

---

## Security Model

| Layer | Implementation |
|---|---|
| API auth | JWT Bearer tokens + `X-API-Key` header, validated on every request |
| RBAC | owner > admin > user > guest, permission matrix on every route |
| Memory isolation | All memory endpoints require `memory_read` / `memory_write` / `memory_wipe` permission |
| Prompt injection | Multi-pattern filter on every `/chat` message |
| Rate limiting | Per-user role-based limits (Redis sliding window, in-memory fallback) |
| Tool approval | HMAC-signed server-side tokens (60s TTL) — client `approved: true` is rejected |
| Python sandbox | AST-checked, dunder blocklist (`__base__`, `__mro__`, `__dict__`...), CPU/RAM limits |
| Shell executor | 3-tier: safe → elevated → root; `dangerous` tier (metacharacters) hard-blocked; `shlex.quote` on all args |
| File reader | `os.path.realpath` + bounds check — path traversal blocked |
| Refresh tokens | Single-use rotation with Redis blacklist; `POST /logout` invalidates immediately |
| CORS | Methods and headers explicitly locked down (no `*`) |
| Secrets | `JWT_SECRET_KEY` and `ASTRA_API_KEY` required at startup — server refuses to start without them |
| K8s | Secrets manifest (`k8s/secrets.yaml`) with `secretRef` in deployment |
| Observability | Jaeger + Prometheus + Grafana (password required, no default) |

---

## Memory System

```
Layer 1 — Working memory
  Last 15 conversation turns, loaded per-request from SQLite (user_id scoped)
  Written back atomically at request end via MemoryTransaction

Layer 2 — Episodic memory
  Past sessions with intent + emotion tags
  Queryable by time range and topic

Layer 3 — Semantic memory
  ChromaDB vector index (BGE-small-en-v1.5 embeddings)
  Decay scoring — recent facts ranked higher
  Contradiction detection before storing new facts
  Priority weighting — name (3x), preference (2x), general (1x)

Layer 4 — Structured facts
  Extracted from every conversation (location, name, preferences)
  Stored via MemoryTransaction (single atomic write per request)
  Indexed into ChromaDB for semantic retrieval
  user_id column on all tables — no data blending between users
```

---

## Agent Loop

```
User: "Why is my CPU spiking when I run the model?"
│
▼
Observe   — complexity: 2, requires_tools: true, requires_reflection: false
│
▼
Plan      — [memory_recall, tool_execute: system_monitor, llm_reply]
│
▼
Act       — memory_recall + tool_execute run concurrently via asyncio.gather
            Ollama calls wrapped in asyncio.to_thread — event loop never blocked
            Observation: CPU 94%, top process: ollama runner (87%)
│
▼
Reflect   — critic pass: does the draft answer the question?
            confidence >= 0.75 → APPROVED
│
▼
Reply     — "Your Ollama runner is using 87% CPU during inference.
             Set num_threads to half your core count..."
```

Available tools: `web_search` · `read_file` · `run_python` · `memory_recall` · `system_monitor` · `git` · `calculate`

---

## Features

| Feature | Status | Notes |
|---|---|---|
| 💬 Chat | ✅ | Pipeline registry, streaming SSE, multi-model routing |
| 🧠 Memory | ✅ | 4-layer hybrid — episodic, semantic, vector, structured. Per-user isolated. |
| 🔐 Auth | ✅ | JWT + RBAC (owner/admin/user/guest), rate limiting per role |
| 🤖 Agent loop | ✅ | ReAct with async parallel tool execution |
| 👁️ Vision | ✅ | LLaVA:7b, WebRTC camera, screen capture, face recognition |
| 🎤 Voice | ✅ | Whisper STT, Kokoro TTS (local) |
| 🌐 Web search | ✅ | DuckDuckGo with citation extraction |
| 🐍 Code sandbox | ✅ | AST-checked Python, CPU/RAM limits, signed approval tokens |
| 🔀 Git tools | ✅ | Status, log, diff, branch, commit proposals (subcommand allowlist) |
| 📁 File reader | ✅ | Read + AI-analyze any local file (path traversal blocked) |
| 💻 System monitor | ✅ | CPU, RAM, disk, top processes |
| 📅 Calendar | ✅ | macOS Calendar + Reminders integration |
| 🏠 Smart home | ✅ | Philips Hue, TinyTuya device control |
| 📊 Observability | ✅ | OpenTelemetry, Prometheus, Grafana, Jaeger, structured logging |
| ♻️ Self-improvement | ✅ | Feedback loop with 3-session quality gate |
| 🐳 Docker | ✅ | 6-container deployment (backend, frontend, ollama, redis, prometheus, grafana, jaeger) |
| 🔒 Privacy | ✅ | 100% local, no data leaves device |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, WebRTC, Tailwind |
| Backend | Python 3.11, FastAPI, async/await throughout |
| LLM runtime | Ollama (phi3:mini, mistral, llava:7b) via pluggable LLMBackend ABC |
| Vector DB | ChromaDB + BGE-small-en-v1.5 |
| Cache | Redis 7 (session-scoped, SHA-256 keyed, user-isolated) |
| Database | SQLite WAL (conversation history, structured facts, usage tracking) |
| Observability | OpenTelemetry + Prometheus + Grafana + Jaeger |
| Deployment | Docker Compose · Kubernetes (with Sealed Secrets) |
| CI | GitHub Actions — ruff lint + 113 pytest tests on every push |

---

## Quick Start

### Requirements

- macOS or Linux
- Python 3.11
- [Ollama](https://ollama.ai) installed and running
- 8GB RAM minimum (16GB recommended for llava)
- 20GB disk for models

### 1. Clone

```bash
git clone https://github.com/TDevViper/Astra_Presonal_ai.git
cd Astra_Presonal_ai
```

### 2. Setup

```bash
python3 -m venv venv311
source venv311/bin/activate
pip install -r backend/requirements.txt
```

### 3. Configure

```bash
cp backend/.env.example backend/.env

# Generate secure secrets (required — server refuses to start without these)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Add to backend/.env:
# JWT_SECRET_KEY=<generated above>
# ASTRA_API_KEY=<generated above>
# SERPER_API_KEY=<optional, for web search>
```

### 4. Pull models

```bash
ollama pull phi3:mini
ollama pull llava:7b        # optional, for vision
```

### 5. Start

```bash
# Direct
cd backend && python main.py

# Docker
docker compose up -d
```

### 6. Open

```
http://localhost:5173   (dev)
http://localhost:3000   (Docker)
```

---

## API

All endpoints require `X-API-Key` header. Protected endpoints additionally require `Authorization: Bearer <jwt>`.

```
POST /auth/register       → Create account
POST /auth/login          → Get JWT access + refresh tokens
POST /auth/refresh        → Rotate refresh token (single-use)
POST /auth/logout         → Invalidate refresh token immediately
GET  /auth/me             → Current user info
POST /chat                → Full pipeline response
POST /chat/stream         → Streaming SSE response
GET  /memory              → Load memory (requires memory_read)
POST /memory              → Update memory (requires memory_write)
DELETE /memory            → Wipe memory (requires memory_wipe)
POST /execute             → Tool execution (signed approval token required)
POST /voice/listen        → Record + transcribe (Whisper)
POST /voice/say           → TTS (Kokoro)
POST /vision/analyze_b64  → Analyze base64 image
GET  /health              → Liveness check (public)
GET  /health/detailed     → Full diagnostics (requires system_stats)
POST /model/switch        → Switch active model (requires model_select)
GET  /knowledge/graph     → Knowledge graph
GET  /observability       → Request traces (requires view_traces)
POST /feedback            → Thumbs up/down (feeds quality gate)
```

---

## Project Structure

```
Astra/
├── docker-compose.yml
├── prometheus.yml
├── k8s/
│   ├── deployment.yaml
│   └── secrets.yaml
├── backend/
│   ├── main.py                      # FastAPI entry point, lifespan manager
│   ├── config.py                    # Config class + Pydantic BaseSettings
│   ├── memory_db.py                 # SQLite WAL — conversations + facts (user_id scoped)
│   ├── core/
│   │   ├── brain.py                 # Slim orchestrator — delegates to pipeline
│   │   ├── brain_singleton.py       # Stateless singleton, no shared history
│   │   ├── pipeline/
│   │   │   ├── base.py              # Handler ABC, RequestContext, Reply
│   │   │   ├── registry.py          # PipelineRegistry — ordered handler chain
│   │   │   ├── handlers.py          # All handler implementations
│   │   │   └── builder.py           # Wires handlers into registry
│   │   ├── llm_backend.py           # LLMBackend ABC + OllamaBackend + StubBackend
│   │   ├── agent_loop.py            # Observe → Plan → Act → Reflect (fully async)
│   │   ├── response_cache.py        # Session-scoped Redis/local cache (1000 entry cap)
│   │   └── truth_guard.py           # Hallucination filter
│   ├── auth/
│   │   ├── jwt_handler.py           # JWT create/verify (HS256)
│   │   ├── rbac.py                  # Role hierarchy + permission matrix
│   │   ├── rate_limiter.py          # Per-user sliding window (Redis pool + in-memory fallback)
│   │   ├── users_db.py              # bcrypt password hashing, SQLite user store
│   │   └── usage_tracker.py         # Per-request usage logging
│   ├── tools/
│   │   ├── shell_executor.py        # 3-tier safety + dangerous tier block + shlex.quote
│   │   ├── python_sandbox.py        # AST-checked + hardened dunder blocklist
│   │   ├── file_reader.py           # Path traversal blocked via realpath + bounds check
│   │   └── git_tool.py              # Subcommand allowlist + metachar rejection
│   ├── api/routers/                 # FastAPI routers (auth, chat, memory, health...)
│   └── tests/                       # 113 passing tests
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
```

---

## Engineering Notes

**`RequestContext` instead of a stateful Brain singleton** — shared mutable conversation history on a singleton causes guaranteed data corruption under concurrent load. `RequestContext` is immutable and per-request.

**Pipeline registry instead of an if-chain** — `brain.py` originally contained a 200-line routing function. The `PipelineRegistry` makes each handler independently testable and additive.

**Signed approval tokens for shell execution** — client-supplied `approved: true` is trivially forged. A server-issued HMAC token with a 60-second TTL cannot be replayed.

**asyncio.to_thread for all LLM calls** — synchronous `ollama.Client().chat()` calls are wrapped so the FastAPI event loop is never blocked. The streaming endpoint uses the async Ollama client directly.

**user_id on all storage tables** — `conversations`, `facts`, and usage tables all carry a `user_id` column with indexes. No data blending is possible even if multiple users share an instance.

**Refresh token single-use rotation** — on every `/auth/refresh`, the old token is blacklisted (Redis TTL matching expiry, in-memory fallback) before a new one is issued. `/auth/logout` blacklists immediately.

**What this is not** — ASTRA is a single-tenant local application. The memory system, session model, and storage layer assume one primary user. Extending to multi-user SaaS requires PostgreSQL with full per-user namespacing and a task queue for LLM inference.

---

## Why I Built This

Most AI assistants are wrappers around cloud APIs. Your data leaves your device, context resets every session, and you have no visibility into what the model is doing.

I built ASTRA to answer a different question: what does a personal AI look like if it runs entirely on your own hardware, remembers you across sessions, and shows you exactly how it reaches every answer?

Every conversation stays on your machine. Every memory is yours.

---

<div align="center">

*Built by Arnav Yadav*

</div>
