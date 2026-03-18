from functools import wraps
import os
import hmac
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.getenv("ASTRA_API_KEY", "")
        if not api_key:
            return jsonify({"error": "ASTRA_API_KEY not configured on server"}), 500
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, api_key):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
