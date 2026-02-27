from dataclasses import dataclass, field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@dataclass
class ModelConfig:
    model_name: str = os.getenv("OLLAMA_MODEL", "phi3:mini")
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "500"))
    top_p: float = float(os.getenv("TOP_P", "0.9"))
    context_window: int = 4096
    max_history: int = 10


@dataclass
class AppConfig:
    host: str = os.getenv("FLASK_HOST", "127.0.0.1")
    port: int = int(os.getenv("FLASK_PORT", "5050"))
    debug: bool = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    memory_file: str = os.path.join(BASE_DIR, "memory", "data", "memory.json")
    max_facts: int = 50
    enable_web_search: bool = os.getenv("ENABLE_WEB_SEARCH", "False").lower() == "true"
    enable_emotions: bool = os.getenv("ENABLE_EMOTIONS", "True").lower() == "true"
    enable_memory: bool = os.getenv("ENABLE_MEMORY", "True").lower() == "true"
    model: Optional[ModelConfig] = None  # ✅ Fixed type hint

    def __post_init__(self):
        self.model = ModelConfig()
        if not os.path.exists(self.memory_file):
            import json
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            with open(self.memory_file, "w") as f:
                json.dump({}, f)


config = AppConfig()