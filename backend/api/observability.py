from flask import Blueprint, jsonify
from core.observability import get_store
from core.event_bus import get_history, get_stats

obs_bp = Blueprint("observability", __name__)


@obs_bp.route("/api/traces", methods=["GET"])
def get_traces():
    return jsonify(
        {
            "traces": get_store().get_recent(20),
            "stats": get_store().get_stats(),
        }
    )


@obs_bp.route("/api/events", methods=["GET"])
def get_events():
    return jsonify(
        {
            "events": get_history(30),
            "stats": get_stats(),
        }
    )
