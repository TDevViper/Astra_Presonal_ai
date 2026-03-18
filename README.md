<div align="center">
```
 █████╗ ███████╗████████╗██████╗  █████╗ 
██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗
███████║███████╗   ██║   ██████╔╝███████║
██╔══██║╚════██║   ██║   ██╔══██╗██╔══██║
██║  ██║███████║   ██║   ██║  ██║██║  ██║
╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
```

**Local Autonomous AI OS · Multi-Agent Architecture · 100% Private**

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen?style=flat-square)](#)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)](https://docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat-square)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Built by Arnav Yadav · Runs 100% locally · No cloud · No API keys*

</div>

---


## UI Preview

> Screenshots coming soon — run locally to see the full interface.
> `docs/images/` folder is ready for contributions.

| Panel | Description |
|---|---|
| Chat Interface | Streaming responses with agent + confidence metadata |
| Agent Trace | Live 12-step pipeline visualization per query |
| Memory Graph | Interactive knowledge graph of learned entities |
| Vision Panel | Real-time camera + screen analysis feed |

---
## What is ASTRA?

ASTRA is a **personal AI operating system** that runs entirely on your machine. It combines multi-agent reasoning, hybrid memory, real-time vision, and voice — all orchestrated through a 12-step processing pipeline with zero data leaving your device.

This is not a chatbot wrapper. It is a full AI system with:
- A **ReAct agent** that reasons step-by-step using tools
- A **knowledge graph** that builds a semantic model of you
- A **critic + refinement pipeline** that reviews every response
- A **truth guard** that catches hallucinations before they reach you
- **Parallel tool execution** for multi-step queries
- **Kokoro TTS** for natural, high-quality local voice output
- **React error boundaries** so UI never crashes silently
- **Model auto-unload** — idle models free RAM automatically

---

## System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                        │
│   Chat · Vision · Memory Graph · Live Pipeline Trace Panel      │
│   ErrorBoundary on every panel — no silent UI crashes           │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    Flask Backend  :5050                          │
│                    API Key auth on all endpoints                 │
│                    Rate limiter · CORS · 18 blueprints           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Brain v5.1 — 12-step pipeline          │    │
│  │                                                          │    │
│  │  Input → Sanitize → Cache → Intent → Tools → Memory     │    │
│  │       → Web Search → ReAct → LLM → Critic → Polish      │    │
│  │                                                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Shortcut │ │  Tools   │ │  ReAct   │ │ Planner  │  │    │
│  │  │ Handler  │ │  Router  │ │  Agent   │ │ Executor │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │                      │                                   │    │
│  │              ┌───────▼──────┐                           │    │
│  │              │  Ollama LLM  │ phi3 · mistral · llava    │    │
│  │              │  Auto-unload │ idle models free RAM       │    │
│  │              └───────┬──────┘                           │    │
│  │                      │                                   │    │
│  │    ┌─────────────────▼──────────────────────────┐      │    │
│  │    │         Post-Processing Pipeline            │      │    │
│  │    │  Critic → Refine → TruthGuard → Polish      │      │    │
│  │    │  → LimitWords → EmotionPrefix → Proactive   │      │    │
│  │    └────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    Memory    │  │   Knowledge  │  │       Vision         │  │
│  │  ─────────  │  │    Graph     │  │  ──────────────────  │  │
│  │  Episodic   │  │  ─────────  │  │  LLaVA:7b Analyzer  │  │
│  │  Semantic   │  │  NetworkX   │  │  WebRTC Camera      │  │
│  │  FAISS Vec  │  │  Entities   │  │  Screen Capture     │  │
│  │  ChromaDB   │  │  Relations  │  │  Face Recognition   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
┌────────▼──────┐   ┌────────▼──────┐   ┌────────▼──────┐
│    Ollama     │   │     Redis     │   │   SQLite DB   │
│  :11434       │   │   :6379       │   │  astra.db     │
│  phi3:mini    │   │   Response    │   │  Chat History │
│  mistral      │   │   Cache       │   │  User Facts   │
│  llava:7b     │   │   mem: 256m   │   └───────────────┘
│  mem: 10g     │   └───────────────┘
└───────────────┘
```

---

## The 12-Step Processing Pipeline

Every message goes through this pipeline before reaching you:
```
User Input
    │
    ▼
 1. clean_text()           — strip noise, normalize
    │
    ▼
 2. _sanitize_input()      — block prompt injection attempts
    │
    ▼
 3. detect_mode_switch()   — focus / creative / precise mode
    │
    ▼
 4. response_cache         — MD5 hash check (600s TTL, Redis)
    │
    ▼
 5. chain_planner          — detect multi-step queries
    │
    ▼
 6. tool_router            — git / file / system / calendar / python
    │
    ▼
 7. intent_shortcuts       — instant replies for known patterns
    │
    ▼
 8. memory_recall          — semantic + episodic + knowledge graph
    │
    ▼
 9. web_search_agent       — DuckDuckGo with citation extraction
    │
    ▼
10. ReAct agent            — Thought → Action → Observation loop
    │
    ▼
11. Ollama LLM             — model selected by query intent
    │
    ▼
12. critic → refine → truth_guard → polish → limit_words → proactive
    │
    ▼
Final Reply
```

---

## ReAct Agent Loop
```
User: "Why is my CPU usage spiking when I run the model?"
         │
         ▼
   Thought: Need to check system stats and running processes
         │
         ▼
   Action: system_monitor(cpu, top_processes)
         │
         ▼
   Observation: CPU 94%, top process: ollama runner (87%)
         │
         ▼
   Thought: The model inference is consuming all cores
         │
         ▼
   Action: memory_recall(ollama performance settings)
         │
         ▼
   Final Answer: "Your Ollama runner is using 87% CPU during
                  inference. Reduce num_predict to 200-300..."
```

Available tools: `web_search` · `read_file` · `run_python` · `memory_recall` · `graph_lookup` · `calculate`

---

## Memory Architecture
```
┌─────────────────────────────────────────────┐
│              Memory Layers                   │
│                                              │
│  Layer 1 — Working Memory                   │
│  └─ Last 12 conversation turns (in-process) │
│                                              │
│  Layer 2 — Episodic Memory                  │
│  └─ Past sessions with intent + emotion tag │
│                                              │
│  Layer 3 — Semantic Memory                  │
│  └─ ChromaDB vector index (primary)         │
│     BGE-small-en-v1.5 embeddings            │
│     Decay scoring — recent = higher rank    │
│     Contradiction detection before store    │
│     Priority weighting (name=3, pref=2)     │
│                                              │
│  Layer 4 — Knowledge Graph                  │
│  └─ NetworkX entity-relation store          │
│     Auto-extracted from every conversation  │
│     User → [likes, works_on, prefers] → X  │
└─────────────────────────────────────────────┘
```

---

## Features

| Feature | Status | Details |
|---|---|---|
| 💬 Chat | ✅ | 12-step pipeline, streaming, multi-model routing |
| 🤖 Multi-Agent | ✅ | ReAct, Planner, Critic, Reasoner, Orchestrator |
| 🧠 Memory | ✅ | FAISS + ChromaDB + Episodic + Knowledge Graph |
| 👁️ Vision | ✅ | LLaVA:7b, WebRTC camera, screen capture, face recognition |
| 🎤 Voice | ✅ | Whisper STT, Kokoro TTS (local, high quality) |
| 🌐 Web Search | ✅ | DuckDuckGo agent with citation extraction |
| 🐍 Code Sandbox | ✅ | AST-checked Python with approval flow |
| 🔀 Git Tools | ✅ | Status, log, diff, branch, commit proposals |
| 📁 File Reader | ✅ | Read + AI-analyze any local file |
| 💻 System Monitor | ✅ | CPU, RAM, disk, top processes |
| 📅 Calendar | ✅ | macOS Calendar + Reminders integration |
| 🏠 Smart Home | ✅ | Philips Hue, TinyTuya device control |
| 📊 Pipeline Trace | ✅ | Live agent decision panel in UI |
| 🔒 Auth | ✅ | API key protection on all endpoints |
| ♻️ RAM Mgmt | ✅ | Models auto-unload after 5min idle |
| 🛡️ Error Boundary | ✅ | React panels never crash the full UI |
| 🐳 Docker | ✅ | 4-container deployment, memory limits set |
| 🔒 Privacy | ✅ | 100% local, no data leaves device |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, WebRTC, Tailwind |
| Backend | Python 3.11, Flask, Flask-CORS, WebSocket |
| LLM Runtime | Ollama (phi3:mini, mistral, llava:7b) |
| Vector DB | FAISS + ChromaDB + BGE-small-en-v1.5 |
| Knowledge Graph | NetworkX + spaCy entity extraction |
| Vision | LLaVA:7b, OpenCV, mss screen capture |
| STT | faster-whisper (tiny model, local) |
| TTS | Kokoro v1 (local neural TTS) |
| Cache | Redis 7 (response cache, 256MB limit) |
| Database | SQLite (chat history, user facts) |
| Deployment | Docker Compose (4 containers, mem limits) |

---


## Why I Built ASTRA

Most AI assistants today are wrappers around cloud APIs — your data leaves your device, context resets every session, and you have no control over the model.

I built ASTRA to answer a different question: **what does a truly personal AI look like if it runs 100% on your own hardware?**

ASTRA is the result — a full AI operating system with persistent memory, multi-agent reasoning, local voice and vision, and zero cloud dependency. Every conversation stays on your machine. Every memory is yours.

---
## Quick Start

### Requirements
- macOS or Linux
- Docker Desktop (optional — can run without)
- 8GB RAM minimum (16GB recommended for llava)
- 20GB disk space for models
- Python 3.11

### 1. Clone
```bash
git clone https://github.com/TDevViper/Astra_Presonal_ai.git
cd Astra_Presonal_ai  # rename to astra-ai-os recommended
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
# SERPER_API_KEY=<optional_for_web_search>
```

### 4. Pull Models
```bash
ollama pull phi3:mini
ollama pull llava:7b
```

### 5. Start
```bash
# Option A — direct
cd backend && python app.py

# Option B — Docker
docker compose up -d
```

### 6. Open
```
http://localhost:5173   (dev)
http://localhost:3000   (Docker)
```

---


## Example Queries
```
"What meetings do I have today?"
"Why is my CPU usage spiking?"
"Analyze this screenshot and tell me what's happening"
"Search for the latest news on AI agents"
"Remember that I prefer dark mode and minimal UI"
"What have we talked about this week?"
"Run this Python script and show me the output"
"Summarize my git changes from today"
"Turn off the living room lights"
"Who is in this photo?"
```

---
## API Reference

All endpoints require `X-API-Key` header when `ASTRA_API_KEY` is set.
```
POST /chat              → Full pipeline chat
POST /chat/stream       → Streaming response with SSE
POST /talk              → Voice + Vision combined
POST /voice/listen      → Record + transcribe (Whisper)
POST /voice/say         → TTS speak text (Kokoro)
POST /vision/analyze_b64→ Analyze base64 image (WebRTC)
POST /vision/screen     → Analyze current screen
GET  /memory            → Load full memory state
DELETE /memory          → Wipe memory
POST /model/switch      → Switch active Ollama model
GET  /health            → System health + model list
POST /execute           → System stats / tool execution
GET  /knowledge/graph   → Knowledge graph data
GET  /api/digest        → Daily digest
```

---


## ASTRA vs Cloud AI

| Feature | ChatGPT / Gemini | ASTRA |
|---|---|---|
| Runs locally | ❌ Cloud only | ✅ 100% on-device |
| Persistent memory | ❌ Resets each session | ✅ 4-layer hybrid memory |
| Your data stays private | ❌ Sent to servers | ✅ Never leaves your machine |
| Vision | ☁️ Cloud processed | ✅ Local LLaVA:7b |
| Voice | ☁️ Cloud processed | ✅ Local Whisper + Kokoro |
| Custom tools | ❌ Limited plugins | ✅ Git, shell, calendar, smart home |
| Works offline | ❌ Needs internet | ✅ Fully offline capable |
| Cost per query | 💰 API billing | ✅ Free after setup |
| Multi-agent reasoning | ⚠️ Basic | ✅ ReAct + Planner + Critic |
| Knowledge graph | ❌ | ✅ Builds model of you over time |

---
## Security Model

| Layer | Protection |
|---|---|
| API auth | `X-API-Key` header on all endpoints |
| Prompt injection | `_sanitize_input()` on every message (chat + stream) |
| Python sandbox | AST-checked, blocked imports, CPU/RAM limits |
| Shell executor | 3-tier safety: safe → elevated → root |
| Rate limiting | 500 req/min via Flask-Limiter + Redis |
| CORS | Whitelist only (localhost dev ports) |

---

## Benchmarks

Measured on Mac M4 (16GB), all models local:

| Metric | Value |
|---|---|
| Average response latency | ~1.8s (phi3:mini) |
| Streaming first token | ~0.4s |
| Memory retrieval (FAISS) | ~35ms |
| ReAct loop (3 steps) | ~4.2s |
| Vision analysis (LLaVA) | ~3.1s |
| Cache hit response | ~12ms |
| Tool execution (system) | ~95ms |
| Test suite | 86 tests, ~20s |

---

## Project Structure
```
Astra/
├── docker-compose.yml         # 4-container setup, memory limits
├── backend/
│   ├── app.py                 # Flask entry point, all blueprints
│   ├── config.py              # Env-based config class
│   ├── core/
│   │   ├── brain.py           # 12-step pipeline orchestrator
│   │   ├── llm_engine.py      # Ollama calls, ReAct trigger
│   │   ├── model_manager.py   # Smart model selection + auto-unload
│   │   ├── truth_guard.py     # Hallucination filter
│   │   ├── response_cache.py  # Redis MD5 cache
│   │   └── post_processor.py  # Critic → refine → polish
│   ├── agents/
│   │   ├── react_agent.py     # ReAct implementation
│   │   ├── planner.py         # Task decomposition
│   │   ├── critic.py          # Output quality review
│   │   └── reasoner.py        # Chain-of-thought
│   ├── memory/
│   │   ├── vector_store.py    # ChromaDB + decay + priority scoring
│   │   ├── memory_extractor.py # Fact extraction from user input
│   │   ├── memory_recall.py   # Structured memory recall
│   │   ├── episodic.py        # Session memory
│   │   └── semantic_recall.py # Similarity search
│   ├── knowledge/
│   │   ├── graph.py           # NetworkX knowledge graph
│   │   └── auto_extractor.py  # Auto-build from chat
│   ├── vision/
│   │   ├── vision_engine.py   # LLaVA integration
│   │   └── face_recognition_engine.py
│   ├── voice/
│   │   ├── listener.py        # Whisper STT
│   │   └── speaker.py         # Kokoro TTS
│   ├── tools/
│   │   ├── tool_router.py     # Tool dispatcher
│   │   ├── shell_executor.py  # 3-tier safety model
│   │   └── python_sandbox.py  # AST-checked execution
│   └── tests/
│       ├── test_brain_pipeline.py   # 40+ pipeline tests
│       ├── test_tool_executor.py    # Tool + face tests
│       ├── test_agent_loop.py
│       └── test_knowledge_graph.py
└── frontend/
    └── src/
        ├── App.jsx                  # Main UI (700 lines)
        └── components/
            ├── ErrorBoundary.jsx    # Catches component crashes
            ├── AgentTrace.jsx       # Live pipeline panel
            ├── KnowledgeGraph.jsx
            └── LiveVision.jsx
```

---

## Roadmap

- [x] WebSocket real-time streaming
- [x] Kokoro TTS (local neural voice)
- [x] API key authentication
- [x] Prompt injection protection
- [x] Model auto-unload (RAM management)
- [x] React ErrorBoundary
- [x] Docker memory limits
- [x] 86-test suite
- [x] Memory hobby/preference extraction + recall
- [x] Vector search threshold tuning
- [x] Dead code cleanup (13 files removed)
- [ ] Temporal frame memory (last 10 frames context)
- [ ] Prometheus + Grafana observability
- [ ] Android companion app
- [ ] GPU server offloading
- [ ] App.jsx component splitting

---

<div align="center">

*Built with 🔥 by Arnav Yadav*

**"Not just an assistant — an AI OS"**

</div>
