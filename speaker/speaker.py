import json
from pathlib import Path
import threading
import requests
import soundfile as sf

import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent / "models" / "vosk" / "vosk-model-small-ru-0.22"
AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

RESPONSE_PATH = Path(__file__).parent / "audio" / "response.wav"

DEVICE_ID = 1
BLOCK_SECONDS = 0.25
SILENCE_RMS = 500
SILENCE_SECONDS = 2
MAX_COMMAND_SECONDS = 15

WAKE_WORDS = ("джарвис", "жарвис", "джарвиз")

is_busy = threading.Event()

def has_wake_word(text):
    return any(word in text for word in WAKE_WORDS)


def text_after_wake(text):
    for word in WAKE_WORDS:
        if word in text:
            return word + " " + text.split(word, 1)[1].strip()
    return ""


def speak(audio_path):
    data, rate = sf.read(audio_path, dtype="float32")
    sd.play(data, rate)
    sd.wait()


def ask_brain(query):
    try:
        response = requests.post(
            "http://127.0.0.1:5000/api/chat",
            json={"text": query},
            timeout=(2, 60),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Сбой запроса: {error!r}")
        return None

    content_type = response.headers.get("Content-Type", "")

    if not content_type.startswith("audio/"):
        print("Сервер вернул не аудио:", response.text[:200])
        return None

    RESPONSE_PATH.write_bytes(response.content)
    return RESPONSE_PATH


def cook(query):
    try:
        print(f"Запрос: {query}")
        audio_path = ask_brain(query)
        if audio_path:
            speak(audio_path)
    finally:
        is_busy.clear()


def cook_async(query):
    is_busy.set()
    threading.Thread(target=cook, args=(query,), daemon=True).start()


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Нет модели Vosk: {MODEL_PATH}")

    model = Model(str(MODEL_PATH))
    mic = sd.query_devices(DEVICE_ID, kind="input")
    rate = int(mic["default_samplerate"])
    block_frames = int(rate * BLOCK_SECONDS)
    max_blocks = int(MAX_COMMAND_SECONDS / BLOCK_SECONDS)

    wake = KaldiRecognizer(model, rate)
    command = None
    leftover = ""
    silence_blocks = 0
    blocks = 0
    speech_seen = False

    print(f"Слушаю ({mic['name']})...")

    with sd.RawInputStream(
        samplerate=rate,
        blocksize=block_frames,
        dtype="int16",
        channels=1,
        device=DEVICE_ID,
    ) as stream:
        while True:
            data, overflowed = stream.read(block_frames)

            if is_busy.is_set():
                continue

            block = bytes(data)

            level = np.sqrt(
                np.mean(np.frombuffer(block, dtype=np.int16).astype(np.float64) ** 2)
            )

            if command is None:
                if wake.AcceptWaveform(block):
                    text = json.loads(wake.Result())["text"]
                    if has_wake_word(text):
                        # screen_glow(True)
                        command = KaldiRecognizer(model, rate)
                        leftover = text_after_wake(text)
                        silence_blocks, blocks, speech_seen = 0, 0, bool(leftover)
                continue

            command.AcceptWaveform(block)
            blocks += 1

            if level > SILENCE_RMS:
                speech_seen = True
                silence_blocks = 0
            else:
                silence_blocks += 1

            finished = (speech_seen
                and silence_blocks * BLOCK_SECONDS >= SILENCE_SECONDS) or blocks >= max_blocks

            if finished:
                text = json.loads(command.FinalResult())["text"]
                query = " ".join(part for part in (leftover, text) if part).strip()

                if query:
                    cook_async(query)

                command = None
                wake = KaldiRecognizer(model, rate)
                # screen_glow(False)


if __name__ == "__main__":
    main()
