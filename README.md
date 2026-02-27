# ◈ ASTRA — Personal AI OS

> Built by Arnav Yadav · Runs 100% locally on Mac M4 · No cloud, no API keys

ASTRA is a multimodal personal AI assistant with chat, voice, vision, and memory — all running locally via Ollama.

---

## 🚀 What It Can Do

| Feature | Status | Details |
|---|---|---|
| 💬 Chat | ✅ | Multi-model routing, intent detection, web search |
| 🎤 Voice | ✅ | STT (Whisper), TTS (macOS Samantha), wake word |
| 👁️ Vision | ✅ | WebRTC camera stream, screen capture, LLaVA analysis |
| 🗣️ Talk | ✅ | Voice + vision combined — speak while showing camera |
| 🧠 Memory | ✅ | Facts, emotions, summaries, ChromaDB vector search |
| 🌐 Web Search | ✅ | DuckDuckGo search agent with citations |
| 🤖 Multi-Agent | ✅ | Reasoner, critic, refinement pipeline |
| 📁 File Reader | ✅ | Read and analyze local files |
| 💻 System Monitor | ✅ | CPU, RAM, disk, top processes |
| 🐍 Python Sandbox | ✅ | Propose and execute Python code |
| 🔀 Git Tools | ✅ | Status, log, branch, diff, commit |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                  Frontend                    │
│         React + Vite (localhost:3000)        │
│   ◈ CHAT tab          ◎ VISION tab          │
│   Voice controls      WebRTC camera          │
│   Memory panel        Talk to ASTRA          │
└──────────────────┬──────────────────────────┘
                   │ HTTP / REST
┌──────────────────▼──────────────────────────┐
│               Flask Backend                  │
│            (localhost:5050)                  │
│                                              │
│  /chat        → Brain pipeline               │
│  /talk        → Voice + Vision combined      │
│  /vision/*    → LLaVA analysis               │
│  /voice/*     → STT / TTS / wake word        │
│  /memory      → Load / save / clear          │
│  /model/*     → Switch Ollama model          │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│                 Ollama                       │
│   phi3:mini   mistral   llama3.2   llava:7b  │
└─────────────────────────────────────────────┘
```

### Backend Modules

```
backend/
├── api/           → Flask blueprints (chat, voice, vision, multimodal)
├── core/          → Brain, model manager, confidence, truth guard
├── agents/        → Reasoner, critic, knowledge agent
├── memory/        → Engine, extractor, semantic recall, ChromaDB
├── emotion/       → Detector, memory, responder
├── vision/        → LLaVA analyzer, capture, vision engine
├── voice/         → Whisper listener, TTS speaker, wake word
├── intents/       → Shortcuts, classifier, mood
├── tools/         → File reader, git, system monitor, python sandbox
├── websearch/     → DuckDuckGo search agent
├── reflection/    → Reply refinement
└── utils/         → Cleaner, polisher, limiter, language detector
```

---

## ⚡ Quick Start

### Requirements

- Mac M4 (or any Mac with Apple Silicon)
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai)

### 1. Clone

```bash
git clone https://github.com/TDevViper/Astra_Presonal_ai.git
cd Astra_Presonal_ai
```

### 2. Pull Models

```bash
ollama pull phi3:mini
ollama pull mistral
ollama pull llama3.2:3b
ollama pull llava:7b
```

### 3. Backend

```bash
cd backend
python -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
python app.py
```

Backend starts at `http://localhost:5050`

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:3000`

---

## 🎤 Voice Setup

Voice uses macOS built-in `say` command (no setup needed) + faster-whisper for STT.

```bash
pip install faster-whisper sounddevice pyttsx3 numpy
```

Test voice:
```bash
curl -X POST http://localhost:5050/voice/say \
  -H "Content-Type: application/json" \
  -d '{"text": "ASTRA online"}'
```

---

## 👁️ Vision Setup

Vision uses your browser's WebRTC camera + LLaVA running in Ollama.

```bash
ollama pull llava:7b
```

In the UI — switch to `◎ VISION` tab → click **START CAMERA** → allow browser camera permission.

**Vision capabilities:**
- 📷 Camera analysis — ASTRA describes what it sees
- 🖥️ Screen capture — analyze your IDE, terminal, browser
- 🎤 Talk mode — speak + show camera, ASTRA responds out loud
- ▶️ Live mode — continuous analysis every 8 seconds

---

## 🧠 Memory System

ASTRA remembers across sessions using:

- **JSON store** — preferences, facts, emotions, summaries
- **ChromaDB** — vector embeddings for semantic search
- **Sentence Transformers** — `all-MiniLM-L6-v2` embeddings

Memory is stored in `backend/memory/data/memory.json`

Clear memory:
```bash
curl -X DELETE http://localhost:5050/memory
```

---

## 🤖 Multi-Model Routing

ASTRA automatically selects the best model per query:

| Query Type | Model |
|---|---|
| Casual chat, greetings | phi3:mini |
| Technical / code | mistral |
| Research / analysis | llama3.2:3b |
| Vision | llava:7b |

Switch model via UI or:
```bash
curl -X POST http://localhost:5050/model/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral:latest"}'
```

---

## 🌐 API Reference

```
POST /chat              → Send message, get reply
POST /talk              → Voice + vision combined
POST /talk/listen       → Record voice → transcribe
POST /voice/say         → TTS speak text
POST /voice/listen      → Record + transcribe
POST /voice/start       → Start wake word mode
POST /vision/screen     → Analyze screen
POST /vision/camera     → Analyze camera (OpenCV)
POST /vision/analyze_b64 → Analyze base64 image (WebRTC)
GET  /vision/last/<src> → Get last snapshot
GET  /memory            → Load memory
DELETE /memory          → Clear memory
POST /model/switch      → Switch Ollama model
GET  /health            → Health check
```

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, WebRTC |
| Backend | Python, Flask, Flask-CORS |
| LLM | Ollama (phi3, mistral, llama3.2, llava) |
| Vision | LLaVA:7b, OpenCV, mss |
| STT | faster-whisper (tiny model) |
| TTS | macOS `say`, pyttsx3 |
| Memory | ChromaDB, sentence-transformers |
| Web Search | DuckDuckGo |

---

## 📁 Project Structure

```
Astra/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── api/
│   ├── core/
│   ├── vision/
│   ├── voice/
│   ├── memory/
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── LiveVision.jsx
│   │       └── ChatMessage.jsx
│   └── package.json
└── README.md
```

---

## 🔮 Roadmap

- [ ] WebSocket real-time streaming responses
- [ ] Temporal frame memory (last 10 frames context)
- [ ] Object tracking across frames
- [ ] Emotion detection from facial expressions
- [ ] Self-improvement loop — log and learn from sessions
- [ ] Android / iOS companion app
- [ ] 3060 server offloading for heavy models

---

*Built with 🔥 by Arnav Yadav*