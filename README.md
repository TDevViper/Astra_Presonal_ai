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
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen?style=flat-square)](#)
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
- A **hybrid memory system** — episodic, semantic (vector), and structured fact storage
- A **ReAct agent loop** with async parallel tool execution via `asyncio.gather`
- A **TruthGuard** hallucination filter on every response
- A **self-improvement loop** with a quality gate — 3 unique sessions must approve a response before it enters the fine-tune dataset
- **Full async FastAPI** backend — no blocking calls on the request path
- **Session-scoped caching** — zero cross-user response leakage
- **Signed approval tokens** for all destructive tool operations

---

## Architecture

```
User Request
     │
     ▼
[FastAPI — main.py]
  Rate limiter (API-key scoped) · CORS · Request ID · OTel tracing
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
- **Single entry point** — `main.py` is the only server. Flask and `app.py` have been removed.

---

## Memory System

```
Layer 1 — Working memory
  Last 15 conversation turns, loaded per-request from SQLite
  Written back atomically at request end via MemoryTransaction

Layer 2 — Episodic memory
  Past sessions with intent + emotion tags
  Queryable by time range and topic

Layer 3 — Semantic memory
  ChromaDB vector index (BGE-small-en-v1.5 embeddings)
  Decay scoring — recent facts ranked higher
  Contradiction detection before storing new facts
  Priority weighting — name (3×), preference (2×), general (1×)

Layer 4 — Structured facts
  Extracted from every conversation (location, name, preferences)
  Stored via MemoryTransaction (single atomic write per request)
  Indexed into ChromaDB for semantic retrieval
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
| 🧠 Memory | ✅ | 4-layer hybrid — episodic, semantic, vector, structured |
| 🤖 Agent loop | ✅ | ReAct with async parallel tool execution |
| 👁️ Vision | ✅ | LLaVA:7b, WebRTC camera, screen capture, face recognition |
| 🎤 Voice | ✅ | Whisper STT, Kokoro TTS (local) |
| 🌐 Web search | ✅ | DuckDuckGo with citation extraction |
| 🐍 Code sandbox | ✅ | AST-checked Python, CPU/RAM limits, signed approval tokens |
| 🔀 Git tools | ✅ | Status, log, diff, branch, commit proposals |
| 📁 File reader | ✅ | Read + AI-analyze any local file |
| 💻 System monitor | ✅ | CPU, RAM, disk, top processes |
| 📅 Calendar | ✅ | macOS Calendar + Reminders integration |
| 🏠 Smart home | ✅ | Philips Hue, TinyTuya device control |
| 🔒 Security | ✅ | Injection filter, signed tool tokens, API-key rate limiting |
| 📊 Observability | ✅ | OpenTelemetry, structured logging, async trace store |
| ♻️ Self-improvement | ✅ | Feedback loop with 3-session quality gate |
| 🐳 Docker | ✅ | 4-container deployment, memory limits |
| 🔒 Privacy | ✅ | 100% local, no data leaves device |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, WebRTC, Tailwind |
| Backend | Python 3.11, FastAPI, async/await throughout |
| LLM runtime | Ollama (phi3:mini, mistral, llava:7b) via pluggable backend |
| Vector DB | ChromaDB + FAISS + BGE-small-en-v1.5 |
| Cache | Redis 7 (session-scoped, SHA-256 keyed) |
| Database | SQLite (conversation history, structured facts) |
| Observability | OpenTelemetry + structured JSON logging |
| Deployment | Docker Compose (4 containers, memory limits) |

---

## Quick Start

### Requirements

- macOS or Linux
- Python 3.11
- [Ollama](https://ollama.ai) installed and running
- 8GB RAM minimum (16GB recommended for llava)
- 20GB disk for models
- Docker Desktop (optional)

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

# Generate a secure API key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Add to backend/.env:
# ASTRA_API_KEY=<your_key>
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

All endpoints require `X-API-Key` header when `ASTRA_API_KEY` is set.

```
POST /chat                → Full pipeline response
POST /chat/stream         → Streaming SSE response
POST /talk                → Voice + Vision combined
POST /voice/listen        → Record + transcribe (Whisper)
POST /voice/say           → TTS (Kokoro)
POST /vision/analyze_b64  → Analyze base64 image
POST /vision/screen       → Analyze current screen
GET  /memory              → Load memory state
DELETE /memory            → Wipe memory
POST /model/switch        → Switch active model
GET  /health              → System health + dependency status
POST /execute             → Tool execution (signed token required)
GET  /knowledge/graph     → Knowledge graph
GET  /api/digest          → Daily digest
GET  /observability       → Request traces
POST /feedback            → Thumbs up/down (feeds quality gate)
```

---

## Security Model

| Layer | Implementation |
|---|---|
| API auth | `X-API-Key` header, validated on every request |
| Prompt injection | Multi-pattern + unicode normalization filter on every message |
| Rate limiting | Per API-key (not IP) via `slowapi` + Redis |
| Tool approval | HMAC-signed server-side tokens with 60s TTL — client `approved: true` is rejected |
| Python sandbox | AST-checked, blocked imports, CPU/RAM limits via `resource` |
| Shell executor | 3-tier safety: safe → elevated → root, with per-tier confirmation |
| Cache isolation | Session-scoped keys — no cross-user response leakage |

---

## Benchmarks

Measured on Mac M4 (16GB), all models local:

| Metric | Value |
|---|---|
| Average response (phi3:mini) | ~1.8s |
| Streaming first token | ~0.4s |
| Cache hit | ~12ms |
| Memory retrieval (ChromaDB) | ~35ms |
| ReAct loop (3 steps, parallel tools) | ~3.8s |
| Vision analysis (LLaVA) | ~3.1s |
| System tool execution | ~95ms |
| Test suite (86 tests) | ~20s |

---

## Project Structure

```
Astra/
├── docker-compose.yml
├── backend/
│   ├── main.py                      # FastAPI entry point, lifespan manager
│   ├── config.py
│   ├── core/
│   │   ├── brain.py                 # Slim orchestrator — delegates to pipeline
│   │   ├── brain_singleton.py       # Stateless singleton, no shared history
│   │   ├── pipeline/
│   │   │   ├── base.py              # Handler ABC, RequestContext, Reply
│   │   │   ├── registry.py          # PipelineRegistry — ordered handler chain
│   │   │   ├── handlers.py          # All handler implementations
│   │   │   └── builder.py           # Wires handlers into registry
│   │   ├── llm_backend.py           # LLMBackend ABC + OllamaBackend + StubBackend
│   │   ├── agent_loop.py            # Observe → Plan → Act → Reflect loop
│   │   ├── memory_manager.py        # Memory façade (load/save/recall)
│   │   ├── response_cache.py        # Session-scoped Redis/local cache
│   │   ├── truth_guard.py           # Hallucination filter
│   │   ├── context_builder.py       # System prompt assembly
│   │   ├── post_processor.py        # Critic → refine → polish
│   │   ├── feedback.py              # Thumbs up/down + 3-session quality gate
│   │   ├── self_improve.py          # Deep LLM scoring for low-confidence replies
│   │   └── observability.py         # Async trace store + OTel
│   ├── agents/
│   │   ├── react_agent.py           # ReAct with asyncio.gather parallel tools
│   │   ├── planner.py
│   │   ├── critic.py
│   │   └── reasoner.py
│   ├── memory/
│   │   ├── memory_engine.py         # JSON persistence
│   │   ├── memory_transaction.py    # Atomic batch-write context manager
│   │   ├── memory_extractor.py      # Fact extraction from user input
│   │   ├── memory_recall.py         # Structured recall
│   │   ├── episodic.py
│   │   ├── semantic_recall.py       # ChromaDB similarity search
│   │   └── vector_store.py          # ChromaDB + decay + priority scoring
│   ├── tools/
│   │   ├── tool_router.py
│   │   ├── shell_executor.py        # 3-tier safety + HMAC token verification
│   │   ├── python_sandbox.py        # AST-checked execution
│   │   └── chain_planner.py
│   ├── api/routers/                 # FastAPI routers
│   └── tests/
│       ├── test_brain_pipeline.py
│       ├── test_tool_executor.py
│       ├── test_agent_loop.py
│       └── test_knowledge_graph.py
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── ErrorBoundary.jsx
            ├── AgentTrace.jsx
            ├── KnowledgeGraph.jsx
            └── LiveVision.jsx
```

---

## Engineering Notes

This project went through a structured audit and refactor cycle. The major decisions:

**`RequestContext` instead of a stateful Brain singleton** — shared mutable conversation history on a singleton causes guaranteed data corruption under concurrent load. Two requests interleave their histories. `RequestContext` is immutable and per-request, loaded from storage at the start and written back at the end.

**Pipeline registry instead of an if-chain** — `brain.py` originally contained a 200-line routing function. Every new capability required editing the same file. The `PipelineRegistry` makes each handler independently testable and additive — new capabilities are new files, not edits to existing ones.

**Signed approval tokens for shell execution** — client-supplied `approved: true` in a request body is trivially forged. A server-issued HMAC token with a 60-second TTL cannot be replayed or fabricated by an attacker who has the API key.

**Feedback quality gate** — a single accidental thumbs-up on a bad response would poison the fine-tune dataset. Requiring 3 approvals from different sessions makes dataset poisoning require coordinated effort rather than a single click.

**What this is not** — ASTRA is a single-tenant local application. It is not architected for multi-user SaaS deployment. The memory system, session model, and storage layer assume one user on one machine. Extending to multi-user requires PostgreSQL with per-user namespacing, a task queue for LLM inference, and JWT-based identity — infrastructure work outside the scope of this project.

---

## Why I Built This

Most AI assistants are wrappers around cloud APIs. Your data leaves your device, context resets every session, and you have no visibility into what the model is doing.

I built ASTRA to answer a different question: what does a personal AI look like if it runs entirely on your own hardware, remembers you across sessions, and shows you exactly how it reaches every answer?

ASTRA is the result. Every conversation stays on your machine. Every memory is yours.

---

<div align="center">

*Built by Arnav Yadav*

</div>
