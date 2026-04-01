import os


def _bool(key: str, default: str = "true") -> bool:
    return os.getenv(key, default).lower() == "true"


def _int(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


class config:
    # Server
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = _int("FLASK_PORT", 5050)
    debug = os.getenv("FLASK_ENV", "production") != "production"

    # Ollama
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    default_model = os.getenv("DEFAULT_MODEL", "phi3:mini")
    vision_model = os.getenv("VISION_MODEL", "llava:7b")
    research_model = os.getenv("RESEARCH_MODEL", "llama3.2:3b")
    technical_model = os.getenv("TECHNICAL_MODEL", "mistral")

    # Token limits
    ollama_num_predict = _int("OLLAMA_NUM_PREDICT", 1024)
    ollama_num_ctx = _int("OLLAMA_NUM_CTX", 8192)

    # Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    memory_dir = os.path.join(BASE_DIR, "memory")
    db_path = os.path.join(BASE_DIR, "astra_memory.db")

    # Features
    enable_memory = _bool("ENABLE_MEMORY")
    enable_emotions = _bool("ENABLE_EMOTIONS")

    # API keys
    serper_api_key = os.getenv("SERPER_API_KEY", "")
    picovoice_api_key = os.getenv("PICOVOICE_API_KEY", "")

    # Uppercase aliases — kept for backward compat with older modules
    OLLAMA_HOST = ollama_host
    DEFAULT_MODEL = default_model
    VISION_MODEL = vision_model
    RESEARCH_MODEL = research_model
    TECHNICAL_MODEL = technical_model
    FLASK_HOST = host
    FLASK_PORT = port
    DEBUG = debug
    REDIS_URL = redis_url
    MEMORY_DIR = memory_dir
    DB_PATH = db_path
    SERPER_API_KEY = serper_api_key
    PICOVOICE_API_KEY = picovoice_api_key


# Module-level aliases for code that does `from config import DEFAULT_MODEL`
OLLAMA_HOST = config.ollama_host
REDIS_URL = config.redis_url
DEFAULT_MODEL = config.default_model
VISION_MODEL = config.vision_model
RESEARCH_MODEL = config.research_model
TECHNICAL_MODEL = config.technical_model
FLASK_HOST = config.host
FLASK_PORT = config.port
DEBUG = config.debug
MEMORY_DIR = config.memory_dir
DB_PATH = config.db_path
SERPER_API_KEY = config.serper_api_key
PICOVOICE_API_KEY = config.picovoice_api_key
OLLAMA_NUM_PREDICT = config.ollama_num_predict
OLLAMA_NUM_CTX = config.ollama_num_ctx

# Model fallback chain
FALLBACK_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
FALLBACK_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ENABLE_CLOUD_FALLBACK = os.getenv("ENABLE_CLOUD_FALLBACK", "false").lower() == "true"
