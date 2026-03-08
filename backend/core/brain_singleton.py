# Shared Brain instance — import this everywhere instead of Brain()
_instance = None

def get_brain():
    global _instance
    if _instance is None:
        from core.brain import Brain
        _instance = Brain()
    return _instance
