import threading, time

class ContinuousVision:
    def __init__(self, broadcast_fn, get_frame_fn, interval=8):
        self.broadcast  = broadcast_fn
        self.get_frame  = get_frame_fn
        self.interval   = interval
        self.last_desc  = ""
        self.running    = False

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                frame = self.get_frame()
                if frame:
                    from vision.llava_analyzer import analyze_image
                    desc = analyze_image(frame, "Describe only what changed. One sentence.")
                    if self._is_significant_change(desc):
                        self.broadcast(f"👁️ I see: {desc}")
                        self.last_desc = desc
            except Exception:
                pass  # TODO: handle
            time.sleep(self.interval)

    def _is_significant_change(self, new_desc: str) -> bool:
        if not self.last_desc:
            return True
        old_words = set(self.last_desc.lower().split())
        new_words = set(new_desc.lower().split())
        overlap   = len(old_words & new_words) / max(len(old_words), 1)
        return overlap < 0.6
