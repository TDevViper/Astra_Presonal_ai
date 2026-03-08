import os, struct, pyaudio
import pvporcupine

ACCESS_KEY = os.getenv("PORCUPINE_KEY", "")

def start_wake_word_listener(on_wake_callback):
    if not ACCESS_KEY:
        print("[WakeWord] No PORCUPINE_KEY in .env — Whisper wake word still active")
        return

    porcupine = pvporcupine.create(
        access_key = ACCESS_KEY,
        keywords   = ["hey siri"]   # swap for custom .ppn file from console.picovoice.com
    )
    pa     = pyaudio.PyAudio()
    stream = pa.open(
        rate              = porcupine.sample_rate,
        channels          = 1,
        format            = pyaudio.paInt16,
        input             = True,
        frames_per_buffer = porcupine.frame_length
    )
    print("[WakeWord] Listening...")
    try:
        while True:
            pcm    = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm    = struct.unpack_from("h" * porcupine.frame_length, pcm)
            if porcupine.process(pcm) >= 0:
                print("[WakeWord] Detected!")
                on_wake_callback()
    finally:
        stream.close()
        pa.terminate()
        porcupine.delete()
