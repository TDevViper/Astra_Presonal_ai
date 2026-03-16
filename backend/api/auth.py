from functools import wraps
import os
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.getenv("ASTRA_API_KEY", "")
        if not api_key:
            return f(*args, **kwargs)
        provided = (
            request.headers.get("X-API-Key") or
            request.args.get("api_key") or
            (request.get_json(silent=True) or {}).get("api_key")
        )
        if provided != api_key:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
