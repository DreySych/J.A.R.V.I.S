import json
from pathlib import Path
import threading
import subprocess

import requests
import soundfile as sf
import sounddevice as sd
import webview
import numpy as np
import base64
from vosk import KaldiRecognizer, Model

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = (
        BASE_DIR.parent
        / "models"
        / "vosk"
        / "vosk-model-small-ru-0.22"
)

AUDIO_DIR = BASE_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
RESPONSE_PATH = AUDIO_DIR / "response.wav"

INPUT_DEVICE = 2
BLOCK_SECONDS = 0.25
SILENCE_RMS = 80
SILENCE_SECONDS = 2
MAX_COMMAND_SECONDS = 15

WAKE_WORDS = ("джарвис", "жарвис", "джарвиз")

screen_window = None
is_busy = threading.Event()


def has_wake_word(text):
    return any(word in text for word in WAKE_WORDS)


def text_after_wake(text):
    for word in WAKE_WORDS:
        if word in text:
            return text.split(word, 1)[1].strip()
    return ""


def is_valid_command(text):
    normalized = text.casefold().strip(" \t\r\n.,!?;:—-«»\"'")
    if not normalized:
        return False
    return not all(
        word.strip(".,!?;:—-«»\"'") in WAKE_WORDS
        for word in normalized.split()
    )


def speak(audio_path):
    try:
        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        screen_window.evaluate_js(f"window.playAIResponse('{audio_b64}');")

        subprocess.run(
            ["aplay", "-D", "plughw:0,0", str(audio_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except Exception as e:
        print(f"Ошибка воспроизведения: {e}")


def screen_glow(enabled=True):
    screen_window.evaluate_js(
        f"window.screenGlow({json.dumps(bool(enabled))});"
    )


def ask_brain(query):
    try:
        response = requests.post(
            "http://192.168.1.11:5000/api/chat",
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
    except Exception as error:
        print(f"Ошибка обработки ответа: {error!r}")
    finally:
        is_busy.clear()


def cook_async(query):
    if is_busy.is_set():
        return
    is_busy.set()
    threading.Thread(target=cook, args=(query,), daemon=True).start()


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Нет модели Vosk: {MODEL_PATH}")

    model = Model(str(MODEL_PATH))

    mic = sd.query_devices(INPUT_DEVICE, kind="input")
    rate = int(mic["default_samplerate"])

    block_frames = int(rate * BLOCK_SECONDS)
    max_blocks = int(MAX_COMMAND_SECONDS / BLOCK_SECONDS)

    wake = KaldiRecognizer(model, rate)
    command = None
    leftover = ""
    command_parts = []
    silence_blocks = 0
    blocks = 0

    print(f"Слушаю ({mic['name']})...")

    with sd.RawInputStream(
            samplerate=rate,
            blocksize=block_frames,
            dtype="int16",
            channels=1,
            device=INPUT_DEVICE,
    ) as stream:
        while True:
            data, overflowed = stream.read(block_frames)

            if is_busy.is_set():
                continue

            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) * 6.0
            audio_data = np.clip(audio_data, -32768, 32767).astype(np.int16)
            block = audio_data.tobytes()

            level = np.sqrt(
                np.mean(
                    np.frombuffer(block, dtype=np.int16)
                    .astype(np.float64) ** 2
                )
            )

            if command is None:
                if wake.AcceptWaveform(block):
                    text = json.loads(wake.Result())["text"]
                    if has_wake_word(text):
                        screen_glow(True)
                        command = KaldiRecognizer(model, rate)
                        leftover = text_after_wake(text)
                        command_parts = []
                        silence_blocks = 0
                        blocks = 0
                continue

            if command.AcceptWaveform(block):
                part = json.loads(command.Result())["text"]
                if part:
                    command_parts.append(part)

            blocks += 1

            if level > SILENCE_RMS:
                silence_blocks = 0
            else:
                silence_blocks += 1

            finished = (
                    silence_blocks * BLOCK_SECONDS >= SILENCE_SECONDS
                    or blocks >= max_blocks
            )

            if finished:
                tail = json.loads(command.FinalResult())["text"]
                query = " ".join(
                    part for part in (leftover, *command_parts, tail) if part
                ).strip()

                if is_valid_command(query):
                    cook_async("Джарвис " + query)

                command = None
                leftover = ""
                command_parts = []
                wake = KaldiRecognizer(model, rate)
                screen_glow(False)


def start_speaker():
    screen_window.events.loaded.wait()
    main()


if __name__ == "__main__":
    screen_window = webview.create_window(
        title="J.A.R.V.I.S.",
        url=str(BASE_DIR / "circle-opt.html"),
        width=800,
        height=800,
    )

    webview.start(start_speaker, http_server=True)
