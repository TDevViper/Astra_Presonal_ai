import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from config import config
from api.chat import chat_bp
from api.memory import memory_bp
from api.model import model_bp
from api.execute import execute_bp
from api.voice import voice_bp
from api.vision import vision_bp
from api.multimodal import multimodal_bp



class ColoredFormatter(logging.Formatter):
    grey     = "\x1b[38;21m"
    green    = "\x1b[32;21m"
    yellow   = "\x1b[33;21m"
    red      = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset    = "\x1b[0m"

    FORMATS = {
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
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)

app = Flask(__name__)
CORS(app)

app.register_blueprint(chat_bp)
app.register_blueprint(memory_bp)
app.register_blueprint(model_bp)
app.register_blueprint(execute_bp)
app.register_blueprint(voice_bp)
app.register_blueprint(vision_bp)
app.register_blueprint(multimodal_bp)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 ASTRA ENGINE STARTING")
    print("=" * 60)
    print(f"📍 Model:       {config.model.model_name if config.model else 'unknown'}")
    print(f"🌡️  Temperature: {config.model.temperature if config.model else 0.7}")
    print(f"🌐 Server:      http://{config.host}:{config.port}")
    print(f"💾 Memory:      {config.enable_memory}")
    print(f"😊 Emotions:    {config.enable_emotions}")
    print("=" * 60 + "\n")

    app.run(debug=config.debug, host=config.host, port=config.port)