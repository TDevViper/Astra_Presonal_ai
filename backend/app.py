import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

from vision.frame_buffer import FrameBuffer
from vision.continuous_vision import ContinuousVision
from api.ws_stream import sock, broadcast

_frame_buffer      = FrameBuffer(maxlen=10)
_continuous_vision = ContinuousVision(
    broadcast_fn = broadcast,
    get_frame_fn = _frame_buffer.latest,
    interval     = 60
)

from config import config
from api.chat import chat_bp
from api.chat_stream import stream_bp
from api.memory import memory_bp
from api.model import model_bp
from api.execute import execute_bp
from api.voice import voice_bp
from api.vision import vision_bp
from api.face import face_bp
from api.multimodal import multimodal_bp
from api.realtime import realtime_bp
from api.health import health_bp
from api.knowledge import knowledge_bp
from api.mode_api import mode_bp as mode_api_bp
from api.system_stats import stats_bp


class ColoredFormatter(logging.Formatter):
    grey     = "\x1b[38;21m"
    green    = "\x1b[32;21m"
    yellow   = "\x1b[33;21m"
    red      = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset    = "\x1b[0m"
    FORMATS  = {
        logging.DEBUG:    grey     + "%(levelname)s - %(message)s" + reset,
        logging.INFO:     green    + "%(levelname)s - %(message)s" + reset,
        logging.WARNING:  yellow   + "%(levelname)s - %(message)s" + reset,
        logging.ERROR:    red      + "%(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(levelname)s - %(message)s" + reset,
    }
    def format(self, record):
        return logging.Formatter(self.FORMATS.get(record.levelno)).format(record)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger("agents.react_agent").setLevel(logging.INFO)
logging.getLogger("agents.reasoner").setLevel(logging.INFO)
logging.getLogger("agents.critic").setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
sock.init_app(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per minute"],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379")
)
CORS(app, origins=[
    "http://localhost:3000", "http://localhost:3001",
    "http://localhost:5173", "http://127.0.0.1:3000",
    "http://127.0.0.1:3001"
])

app.register_blueprint(chat_bp)
app.register_blueprint(stream_bp)
app.register_blueprint(memory_bp)
app.register_blueprint(model_bp)
app.register_blueprint(execute_bp)
app.register_blueprint(voice_bp)
app.register_blueprint(vision_bp)
app.register_blueprint(face_bp)
app.register_blueprint(multimodal_bp)
app.register_blueprint(realtime_bp)
app.register_blueprint(health_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(mode_api_bp)
app.register_blueprint(stats_bp)


@app.route("/api/frame", methods=["POST"])
def receive_frame():
    from flask import request
    data  = request.get_json()
    frame = data.get("frame")
    if frame:
        _frame_buffer.add(frame)
    return {"ok": True}

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


from core.wake_word import start_wake_word_listener
from core.proactive import set_broadcast
from api.ws_stream import broadcast as _ws_broadcast
set_broadcast(_ws_broadcast)

from core.gpu_health import start as _start_gpu_health
from core.brain_singleton import get_brain, teardown_brain
_start_gpu_health()

@app.teardown_appcontext
def _teardown_brain(exc):
    teardown_brain(exc)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 ASTRA ENGINE STARTING")
    print("=" * 60)
    print(f"📍 Model:       {config.default_model}")
    print(f"🌐 Server:      http://{config.host}:{config.port}")
    print(f"💾 Memory:      {config.enable_memory}")
    print(f"😊 Emotions:    {config.enable_emotions}")
    print(f"🦙 Ollama:      {config.ollama_host}")
    print("=" * 60 + "\n")

    from voice.speaker import speak
    from proactive.proactive_engine import get_proactive_engine
    proactive = get_proactive_engine(speak_fn=speak)
    proactive.start()

    app.run(debug=config.debug, host=config.host, port=config.port)
