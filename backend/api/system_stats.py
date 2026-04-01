import logging
import psutil
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)
stats_bp = Blueprint("system_stats", __name__)


@stats_bp.route("/system/stats", methods=["GET"])
def system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return jsonify(
            {
                "cpu": {"percent": cpu},
                "memory": {
                    "percent": ram.percent,
                    "used_gb": round(ram.used / 1e9, 1),
                    "total_gb": round(ram.total / 1e9, 1),
                },
                "disk": {
                    "percent": disk.percent,
                    "used_gb": round(disk.used / 1e9, 1),
                    "total_gb": round(disk.total / 1e9, 1),
                },
            }
        )
    except Exception as e:
        logger.error("system_stats error: %s", e)
        return jsonify({"error": str(e)}), 500
