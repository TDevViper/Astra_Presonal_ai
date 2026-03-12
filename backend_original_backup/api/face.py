# api/face.py
import logging
from flask import Blueprint, request, jsonify

logger  = logging.getLogger(__name__)
face_bp = Blueprint("face_api", __name__)


@face_bp.route("/face/identify", methods=["POST"])
def identify():
    """POST {image: base64} → who is in the image?"""
    data      = request.get_json()
    image_b64 = data.get("image", "")
    if not image_b64:
        return jsonify({"error": "No image provided"}), 400
    from vision.face_recognition_engine import identify_faces
    result = identify_faces(image_b64)
    return jsonify(result)


@face_bp.route("/face/learn", methods=["POST"])
def learn():
    """POST {name: str, image: base64} → learn this face"""
    data      = request.get_json()
    name      = data.get("name", "").strip()
    image_b64 = data.get("image", "")
    if not name or not image_b64:
        return jsonify({"error": "name and image required"}), 400
    from vision.face_recognition_engine import learn_face
    result = learn_face(name, image_b64)
    return jsonify(result)


@face_bp.route("/face/list", methods=["GET"])
def list_faces():
    from vision.face_recognition_engine import list_known_faces
    return jsonify(list_known_faces())


@face_bp.route("/face/forget", methods=["POST"])
def forget():
    data = request.get_json()
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    from vision.face_recognition_engine import forget_face
    return jsonify(forget_face(name))
