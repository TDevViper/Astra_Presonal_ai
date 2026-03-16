# vision/face_recognition_engine.py
# Fully offline face recognition — learn faces, identify from camera
# Uses face_recognition (dlib) — no cloud, no API
import os, json, logging, base64
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FACES_DIR    = os.path.join(_BACKEND_DIR, "data", "known_faces")
_ENCODINGS_DB = os.path.join(_BACKEND_DIR, "data", "face_encodings.json")

os.makedirs(_FACES_DIR, exist_ok=True)


def _load_db() -> Dict:
    try:
        if os.path.exists(_ENCODINGS_DB):
            with open(_ENCODINGS_DB) as _f:
                return json.load(_f)
    except Exception as e:
        logger.warning("face_db load failed: %s", e)
    return {}


def _save_db(db: Dict):
    try:
        json.dump(db, open(_ENCODINGS_DB, "w"), indent=2)
    except Exception as e:
        logger.warning("face_db save failed: %s", e)


def learn_face(name: str, image_b64: str) -> Dict:
    """
    Learn a new face from a base64 image.
    ASTRA say: 'remember this person, their name is Arnav'
    """
    try:
        import face_recognition
        import numpy as np
        from PIL import Image
        import io

        # Decode image
        img_data = base64.b64decode(image_b64)
        img      = Image.open(io.BytesIO(img_data)).convert("RGB")
        img_arr  = np.array(img)

        # Find face encodings
        locations = face_recognition.face_locations(img_arr, model="hog")
        if not locations:
            return {"success": False, "error": "No face found in image"}

        encodings = face_recognition.face_encodings(img_arr, locations)
        if not encodings:
            return {"success": False, "error": "Could not encode face"}

        # Store encoding
        db = _load_db()
        db[name] = {
            "encoding": encodings[0].tolist(),
            "learned_at": __import__("datetime").datetime.now().isoformat(),
            "face_count": len(locations),
        }
        _save_db(db)

        # Save face image
        face_path = os.path.join(_FACES_DIR, f"{name}.jpg")
        img.save(face_path)

        logger.info("Learned face: %s", name)
        return {"success": True, "name": name, "message": f"Got it — I'll recognize {name} from now on."}

    except ImportError:
        return {"success": False, "error": "face_recognition library not installed. Run: pip install face-recognition"}
    except Exception as e:
        logger.error("learn_face error: %s", e)
        return {"success": False, "error": str(e)}


def identify_faces(image_b64: str, tolerance: float = 0.55) -> Dict:
    """
    Identify all faces in an image.
    Returns list of recognized names + unknowns.
    """
    try:
        import face_recognition
        import numpy as np
        from PIL import Image
        import io

        db = _load_db()
        if not db:
            return {
                "success": True,
                "faces_found": 0,
                "identified": [],
                "unknown": 0,
                "message": "No faces learned yet. Show me someone and say 'remember this person as [name]'."
            }

        # Decode + encode query image
        img_data  = base64.b64decode(image_b64)
        img       = Image.open(io.BytesIO(img_data)).convert("RGB")
        img_arr   = np.array(img)
        locations = face_recognition.face_locations(img_arr, model="hog")

        if not locations:
            return {"success": True, "faces_found": 0, "identified": [],
                    "unknown": 0, "message": "No faces detected in the image."}

        encodings = face_recognition.face_encodings(img_arr, locations)

        # Known encodings
        known_names     = list(db.keys())
        known_encodings = [np.array(db[n]["encoding"]) for n in known_names]

        identified = []
        unknown    = 0

        for encoding in encodings:
            distances = face_recognition.face_distance(known_encodings, encoding)
            if len(distances) == 0:
                unknown += 1
                continue
            best_idx  = int(distances.argmin())
            best_dist = float(distances[best_idx])
            if best_dist <= tolerance:
                identified.append({
                    "name":       known_names[best_idx],
                    "confidence": round(1.0 - best_dist, 2),
                })
            else:
                unknown += 1

        total = len(locations)
        if identified:
            names = ", ".join(f"{r['name']} ({int(r['confidence']*100)}%)"
                              for r in identified)
            if unknown > 0:
                message = f"I can see {names} and {unknown} unknown person(s)."
            else:
                message = f"I can see {names}."
        else:
            message = f"I see {total} face(s) but don't recognize anyone."

        return {
            "success":    True,
            "faces_found": total,
            "identified": identified,
            "unknown":    unknown,
            "message":    message,
        }

    except ImportError:
        return {"success": False, "error": "face_recognition not installed"}
    except Exception as e:
        logger.error("identify_faces error: %s", e)
        return {"success": False, "error": str(e)}


def list_known_faces() -> Dict:
    db = _load_db()
    if not db:
        return {"count": 0, "names": [], "message": "No faces learned yet."}
    names = list(db.keys())
    return {
        "count":   len(names),
        "names":   names,
        "message": f"I know {len(names)} face(s): {', '.join(names)}."
    }


def forget_face(name: str) -> Dict:
    db = _load_db()
    if name not in db:
        return {"success": False, "message": f"I don't know anyone named {name}."}
    del db[name]
    _save_db(db)
    face_path = os.path.join(_FACES_DIR, f"{name}.jpg")
    if os.path.exists(face_path):
        os.remove(face_path)
    return {"success": True, "message": f"Forgot {name}."}
