import os

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Models
DEFAULT_MODEL   = os.getenv("DEFAULT_MODEL", "phi3:mini")
VISION_MODEL    = os.getenv("VISION_MODEL",  "llava:7b")
RESEARCH_MODEL  = os.getenv("RESEARCH_MODEL", "llama3.2:3b")
TECHNICAL_MODEL = os.getenv("TECHNICAL_MODEL", "mistral")

# Flask
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5050))
DEBUG      = os.getenv("FLASK_ENV", "production") != "production"

# Memory paths
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR  = os.path.join(BASE_DIR, "memory")
DB_PATH     = os.path.join(BASE_DIR, "astra_memory.db")

# API keys
SERPER_API_KEY    = os.getenv("SERPER_API_KEY", "")
PICOVOICE_API_KEY = os.getenv("PICOVOICE_API_KEY", "")

# Features
ENABLE_MEMORY   = os.getenv("ENABLE_MEMORY", "true").lower() == "true"
ENABLE_EMOTIONS = os.getenv("ENABLE_EMOTIONS", "true").lower() == "true"

# Backward compat class — covers every config.xyz used in app.py
class config:
    # server
    host  = FLASK_HOST
    port  = FLASK_PORT
    debug = DEBUG

    # features
    enable_memory   = ENABLE_MEMORY
    enable_emotions = ENABLE_EMOTIONS

    # ollama
    ollama_host     = OLLAMA_HOST
    default_model   = DEFAULT_MODEL
    vision_model    = VISION_MODEL
    research_model  = RESEARCH_MODEL
    technical_model = TECHNICAL_MODEL

    # redis
    redis_url = REDIS_URL

    # paths
    memory_dir = MEMORY_DIR
    db_path    = DB_PATH

    # keys
    serper_api_key    = SERPER_API_KEY
    picovoice_api_key = PICOVOICE_API_KEY

    # uppercase aliases
    OLLAMA_HOST       = OLLAMA_HOST
    REDIS_URL         = REDIS_URL
    DEFAULT_MODEL     = DEFAULT_MODEL
    VISION_MODEL      = VISION_MODEL
    RESEARCH_MODEL    = RESEARCH_MODEL
    TECHNICAL_MODEL   = TECHNICAL_MODEL
    FLASK_HOST        = FLASK_HOST
    FLASK_PORT        = FLASK_PORT
    DEBUG             = DEBUG
    MEMORY_DIR        = MEMORY_DIR
    DB_PATH           = DB_PATH
    SERPER_API_KEY    = SERPER_API_KEY
    PICOVOICE_API_KEY = PICOVOICE_API_KEY
