from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class PipelineContext:
    user_input: str; memory: Dict; user_name: str
    emotion_label: str = "neutral"; emotion_score: float = 0.0
    query_intent: str = "general"; selected_model: str = "phi3:mini"
    semantic_ctx: str = ""; sem_confidence: float = 0.0
    episodic_ctx: str = ""; tool_context: str = ""
    memory_updated: bool = False; history: List[Dict] = field(default_factory=list)
