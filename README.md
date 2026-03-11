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
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?style=flat-square&logo=docker)](https://docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat-square)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

*Built by Arnav Yadav · Runs 100% locally · No cloud · No API keys*

</div>

---

## What is ASTRA?

ASTRA is a **personal AI operating system** that runs entirely on your machine. It combines multi-agent reasoning, hybrid memory, real-time vision, and voice — all orchestrated through a 12-step processing pipeline with zero data leaving your device.

This is not a chatbot wrapper. It is a full AI system with:
- A **ReAct agent** that reasons step-by-step using tools
- A **knowledge graph** that builds a semantic model of you
- A **critic + refinement pipeline** that reviews every response
- A **truth guard** that catches hallucinations before they reach you
- **Parallel tool execution** for multi-step queries

---

## System Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                        │
│   Chat · Vision · Memory Graph · Live Pipeline Trace Panel      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    Flask Backend  :5001                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Orchestrator                           │    │
│  │                                                          │    │
│  │  Input → Intent Detection → Route to Agent              │    │
│  │                                                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ Shortcut │ │  Tools   │ │  ReAct   │ │ Planner  │  │    │
│  │  │ Handler  │ │  Router  │ │  Agent   │ │ Executor │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  │                      │                                   │    │
│  │              ┌───────▼──────┐                           │    │
│  │              │  Ollama LLM  │ phi3 · mistral · llava    │    │
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
│  │  Semantic   │  │  Neo4j-like │  │  WebRTC Camera      │  │
│  │  FAISS Vec  │  │  Entities   │  │  Screen Capture     │  │
│  │  ChromaDB   │  │  Relations  │  │  Continuous Vision  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
┌────────▼──────┐   ┌────────▼──────┐   ┌────────▼──────┐
│    Ollama     │   │     Redis     │   │   SQLite DB   │
│  :11434       │   │   :6379       │   │  astra.db     │
│  phi3:mini    │   │   Response    │   │  Chat History │
│  mistral      │   │   Cache       │   │  User Facts   │
│  llama3.2     │   └───────────────┘   └───────────────┘
│  llava:7b     │
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
 2. detect_mode_switch()   — focus / creative / precise mode
    │
    ▼
 3. response_cache         — MD5 hash check (60s TTL, Redis)
    │
    ▼
 4. chain_planner          — detect multi-step queries
    │
    ▼
 5. tool_router            — git / file / system / calendar / python
    │
    ▼
 6. intent_shortcuts       — instant replies for known patterns
    │
    ▼
 7. memory_recall          — semantic + episodic + knowledge graph
    │
    ▼
 8. web_search_agent       — DuckDuckGo with citation extraction
    │
    ▼
 9. ReAct agent            — Thought → Action → Observation loop
    │
    ▼
10. Ollama LLM             — model selected by query intent
    │
    ▼
11. critic_review()        — quality check on output
    │
    ▼
12. refine → truth_guard → polish → limit_words → proactive
    │
    ▼
 Final Reply
```

---

## ReAct Agent Loop

For reasoning queries, ASTRA uses a full ReAct implementation:
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
   Observation: num_predict=600 found in past config
         │
         ▼
   Final Answer: "Your Ollama runner is using 87% CPU during
                  inference. Reduce num_predict to 200-300..."
```

Available tools inside ReAct: `web_search` · `read_file` · `run_python` · `memory_recall` · `graph_lookup` · `calculate`

---

## Memory Architecture

ASTRA uses a 4-layer hybrid memory system:
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
│  └─ FAISS vector index (sentence-transformers│
│     all-MiniLM-L6-v2, 384-dim embeddings)   │
│                                              │
│  Layer 4 — Knowledge Graph                  │
│  └─ Entity-relation store built from every  │
│     conversation (auto_extractor.py)         │
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
| 👁️ Vision | ✅ | LLaVA:7b, WebRTC camera, screen capture, live mode |
| 🎤 Voice | ✅ | Whisper STT, TTS, wake word detection |
| 🌐 Web Search | ✅ | DuckDuckGo agent with citation extraction |
| 🐍 Code Sandbox | ✅ | Propose + execute Python with approval flow |
| 🔀 Git Tools | ✅ | Status, log, diff, branch, commit proposals |
| 📁 File Reader | ✅ | Read + AI-analyze any local file |
| 💻 System Monitor | ✅ | CPU, RAM, disk, top processes |
| 📅 Calendar | ✅ | macOS Calendar + Reminders integration |
| 🏠 Smart Home | ✅ | Philips Hue, TinyTuya device control |
| 📊 Pipeline Trace | ✅ | Live agent decision panel in UI |
| 🐳 Docker | ✅ | 4-container deployment, Redis cache |
| 🔒 Privacy | ✅ | 100% local, no data leaves device |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, WebRTC, Tailwind |
| Backend | Python 3.11, Flask, Flask-CORS, WebSocket |
| LLM Runtime | Ollama (phi3:mini, mistral, llama3.2, llava:7b) |
| Vector DB | FAISS + ChromaDB + sentence-transformers |
| Knowledge Graph | NetworkX + spaCy entity extraction |
| Vision | LLaVA:7b, OpenCV, mss screen capture |
| STT | faster-whisper (tiny model, local) |
| TTS | Kokoro / macOS say |
| Cache | Redis 7 (response cache, session store) |
| Database | SQLite (chat history, user facts) |
| Deployment | Docker Compose (4 containers) |

---

## Quick Start

### Requirements
- Docker Desktop
- 8GB RAM minimum (16GB recommended for llava)
- 20GB disk space for models

### 1. Clone
```bash
git clone https://github.com/TDevViper/Astra_Presonal_ai.git
cd Astra_Presonal_ai
```

### 2. Configure
```bash
cp .env.example .env
# Add your SERPER_API_KEY for web search (optional)
```

### 3. Launch
```bash
docker compose up -d
```

### 4. Pull Models
```bash
docker exec astra_ollama ollama pull phi3:mini
docker exec astra_ollama ollama pull mistral
docker exec astra_ollama ollama pull llama3.2:3b
docker exec astra_ollama ollama pull llava:7b
```

### 5. Open
```
http://localhost:3000
```

---

## API Reference
```
POST /chat              → Full pipeline chat
POST /chat/stream       → Streaming response with SSE
POST /talk              → Voice + Vision combined
POST /voice/listen      → Record + transcribe (Whisper)
POST /voice/say         → TTS speak text
POST /vision/analyze_b64→ Analyze base64 image (WebRTC)
POST /vision/screen     → Analyze current screen
GET  /memory            → Load full memory state
DELETE /memory          → Wipe memory
POST /model/switch      → Switch active Ollama model
GET  /health            → System health + model list
POST /execute           → System stats / tool execution
GET  /knowledge/graph   → Knowledge graph data
```

---

## Project Structure
```
Astra/
├── docker-compose.yml
├── backend/
│   ├── app.py                 # Flask entry point
│   ├── config.py              # Environment config
│   ├── core/
│   │   ├── brain.py           # Main 12-step pipeline
│   │   ├── orchestrator.py    # Multi-agent router
│   │   ├── agent_loop.py      # Autonomous agent loop
│   │   ├── model_manager.py   # Smart model selection
│   │   ├── truth_guard.py     # Hallucination filter
│   │   └── self_improve.py    # Response quality logger
│   ├── agents/
│   │   ├── react_agent.py     # ReAct implementation
│   │   ├── planner.py         # Task decomposition
│   │   ├── critic.py          # Output quality review
│   │   └── reasoner.py        # Chain-of-thought
│   ├── memory/
│   │   ├── memory_engine.py   # Core memory store
│   │   ├── vector_store.py    # FAISS operations
│   │   ├── episodic.py        # Session memory
│   │   └── semantic_recall.py # Similarity search
│   ├── knowledge/
│   │   ├── graph.py           # Knowledge graph
│   │   ├── entity_extractor.py# spaCy NER
│   │   └── auto_extractor.py  # Auto-build from chat
│   ├── vision/
│   │   ├── vision_engine.py   # LLaVA integration
│   │   ├── screen_watcher.py  # Screen capture
│   │   └── continuous_vision.py# Live analysis loop
│   ├── voice/
│   │   ├── listener.py        # Whisper STT
│   │   ├── speaker.py         # TTS engine
│   │   └── wake_word.py       # Porcupine wake word
│   └── tools/
│       ├── tool_router.py     # Tool dispatcher
│       ├── react_agent.py     # ReAct tool runner
│       ├── git_tool.py        # Git operations
│       ├── python_sandbox.py  # Code execution
│       ├── system_monitor.py  # System stats
│       └── chain_planner.py   # Multi-tool chains
└── frontend/
    ├── src/
    │   ├── App.jsx            # Main UI
    │   └── components/
    │       ├── AgentTrace.jsx # Live pipeline panel
    │       ├── KnowledgeGraph.jsx
    │       ├── LiveVision.jsx
    │       └── ProactiveAlerts.jsx
    └── Dockerfile
```

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

---

## Roadmap

- [ ] WebSocket real-time streaming
- [ ] Temporal frame memory (last 10 frames context)
- [ ] Prometheus + Grafana observability dashboard
- [ ] Full pytest test suite
- [ ] Android companion app
- [ ] GPU server offloading

---

<div align="center">

*Built with 🔥 by Arnav Yadav*

**"Not just an assistant — an AI OS"**

</div>
