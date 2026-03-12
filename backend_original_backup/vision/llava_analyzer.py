from vision.analyzer import analyze

def analyze_image(image_b64: str, prompt: str) -> str:
    """Shim expected by screen_watcher.py — delegates to analyzer.py"""
    result = analyze(image_b64, mode="screen", user_context=prompt)
    return result.get("jarvis_response") or result.get("summary", "Unable to analyze.")
