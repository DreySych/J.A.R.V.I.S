from pathlib import Path
import wave
from piper import PiperVoice

BASE_DIR = Path(__file__).resolve().parent.parent
PIPER_MODEL_PATH = BASE_DIR / "models" / "piper" / "ru_RU-ruslan-medium.onnx"

voice = PiperVoice.load(PIPER_MODEL_PATH)


def add_comma_after_sentence(text):
    text = text.strip()

    text.replace(".", ",")

    return text


def synthesize_wav_piper(text, out_path):
    text = add_comma_after_sentence(text)
    with wave.open(out_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
