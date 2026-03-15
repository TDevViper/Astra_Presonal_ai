# voice/conversation_voice.py
# Always-on voice with conversation carry-over
# After ASTRA responds, stays listening for 8s without needing wake word
import threading, time, logging, queue
from typing import Optional, Callable

logger = logging.getLogger(__name__)

_LISTEN_AFTER_RESPONSE = 8.0   # seconds to keep listening after ASTRA speaks
_SILENCE_TIMEOUT       = 2.0   # seconds of silence = end of utterance
_MIN_UTTERANCE_WORDS   = 2     # ignore single-word noise


class ConversationVoice:
    """
    Drop-in replacement for single-shot wake word listener.
    Maintains a conversation_active window so user can speak
    follow-ups without saying "Hey ASTRA" again.
    """

    def __init__(self, process_fn: Callable[[str], str],
                 speak_fn: Callable[[str], None]):
        self.process_fn       = process_fn   # brain.process or similar
        self.speak_fn         = speak_fn
        self._active          = False
        self._conversation_on = False
        self._conversation_timer: Optional[threading.Timer] = None
        self._interrupt_flag  = False
        self._text_queue: queue.Queue = queue.Queue()

    def start(self):
        self._active = True
        threading.Thread(target=self._wake_loop,   daemon=True).start()
        threading.Thread(target=self._process_loop, daemon=True).start()
        logger.info("🎙️  ConversationVoice started")

    def stop(self):
        self._active = False
        logger.info("🎙️  ConversationVoice stopped")

    def _transcribe(self) -> Optional[str]:
        """Transcribe one utterance using faster-whisper."""
        try:
            import sounddevice as sd
            import numpy as np
            sample_rate = 16000
            chunk_size  = int(sample_rate * 0.5)   # 0.5s chunks
            audio_chunks = []
            silence_count = 0
            max_silence = int(_SILENCE_TIMEOUT / 0.5)

            with sd.InputStream(samplerate=sample_rate, channels=1,
                                dtype="float32", blocksize=chunk_size) as stream:
                while self._active:
                    chunk, _ = stream.read(chunk_size)
                    rms = float(np.sqrt(np.mean(chunk**2)))
                    if rms > 0.01:     # voice activity
                        audio_chunks.append(chunk)
                        silence_count = 0
                    elif audio_chunks:  # trailing silence
                        silence_count += 1
                        audio_chunks.append(chunk)
                        if silence_count >= max_silence:
                            break

            if not audio_chunks:
                return None

            audio = np.concatenate(audio_chunks).flatten()

            from faster_whisper import WhisperModel
            model  = WhisperModel("tiny", device="cpu", compute_type="int8")
            segs, _= model.transcribe(audio, language="en")
            text   = " ".join(s.text for s in segs).strip()
            return text if len(text.split()) >= _MIN_UTTERANCE_WORDS else None

        except Exception as e:
            logger.debug("transcribe error: %s", e)
            return None

    def _wake_loop(self):
        """Listen for wake word OR conversation window."""
        while self._active:
            try:
                if self._conversation_on:
                    # No wake word needed — just transcribe
                    text = self._transcribe()
                    if text:
                        logger.info("🎙️  [conv] %s", text)
                        self._text_queue.put(text)
                else:
                    # Wait for wake word
                    detected = self._check_wake_word()
                    if detected:
                        self._conversation_on = True
                        self._reset_conv_timer()
                        text = self._transcribe()
                        if text:
                            self._text_queue.put(text)
                time.sleep(0.1)
            except Exception as e:
                logger.debug("wake_loop error: %s", e)
                time.sleep(1)

    def _check_wake_word(self) -> bool:
        """Check for wake word using pvporcupine if available."""
        try:
            import pvporcupine
            import sounddevice as sd
            import numpy as np
            key   = __import__("os").getenv("PICOVOICE_API_KEY", "")
            if not key:
                time.sleep(0.5)
                return False
            porcupine = pvporcupine.create(
                access_key=key, keywords=["hey siri"]  # fallback keyword
            )
            chunk = sd.rec(porcupine.frame_length, samplerate=porcupine.sample_rate,
                           channels=1, dtype="int16")
            sd.wait()
            result = porcupine.process(chunk.flatten())
            porcupine.delete()
            return result >= 0
        except Exception:
            time.sleep(0.5)
            return False

    def _reset_conv_timer(self):
        """Reset the conversation window timer."""
        if self._conversation_timer:
            self._conversation_timer.cancel()
        self._conversation_timer = threading.Timer(
            _LISTEN_AFTER_RESPONSE, self._end_conversation
        )
        self._conversation_timer.daemon = True
        self._conversation_timer.start()

    def _end_conversation(self):
        self._conversation_on = False
        logger.info("🎙️  Conversation window closed")

    def _process_loop(self):
        """Process transcribed text through brain."""
        while self._active:
            try:
                text = self._text_queue.get(timeout=1.0)
                logger.info("🗣️  Processing: %s", text)
                result = self.process_fn(text)
                reply  = result.get("reply", "") if isinstance(result, dict) else str(result)

                # Interrupt current speech if user spoke
                self._interrupt_flag = True
                time.sleep(0.1)
                self._interrupt_flag = False

                self.speak_fn(reply)
                # Extend conversation window after ASTRA responds
                self._conversation_on = True
                self._reset_conv_timer()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error("process_loop error: %s", e)

    def interrupt(self):
        """Call this when user starts speaking to stop ASTRA mid-sentence."""
        self._interrupt_flag = True
