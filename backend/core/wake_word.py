import os, struct, threading
import pvporcupine
import pyaudio

ACCESS_KEY = os.getenv("PORCUPINE_KEY", "")
PPN_PATH   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "Hey-ASTRA_en_mac_v4_0_0.ppn")

def start_wake_word_listener(on_wake_callback):
    if not ACCESS_KEY:
        print("[WakeWord] No PORCUPINE_KEY set — skipping")
        return

    def _listen():
        try:
            porcupine = pvporcupine.create(
                access_key        = ACCESS_KEY,
                keyword_paths     = [PPN_PATH]
            )
            pa     = pyaudio.PyAudio()
            stream = pa.open(
                rate              = porcupine.sample_rate,
                channels          = 1,
                format            = pyaudio.paInt16,
                input             = True,
                frames_per_buffer = porcupine.frame_length
            )
            print("[WakeWord] ✅ Say 'Hey Astra' to activate...")
            while True:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    print("[WakeWord] 🎤 Hey Astra detected!")
                    on_wake_callback()
        except Exception as e:
            print(f"[WakeWord] Error: {e}")

    threading.Thread(target=_listen, daemon=True).start()
