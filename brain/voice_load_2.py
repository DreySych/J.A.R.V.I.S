from pathlib import Path
import io
import re
import wave

import numpy as np
import soundfile as sf
import sounddevice as sd

from piper import PiperVoice

BASE_DIR = Path(__file__).resolve().parent.parent
PIPER_MODEL_PATH = BASE_DIR / "models" / "piper" / "ru_RU-ruslan-medium.onnx"

voice = PiperVoice.load(PIPER_MODEL_PATH)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text):
    text = " ".join(text.split())
    if not text:
        return []

    parts = [part.strip() for part in SENTENCE_SPLIT.split(text) if part.strip()]

    result = []
    for part in parts:
        if not part[-1] in ".!?…":
            part += "."
        result.append(part)

    return result


def synthesize_sentence(sentence):
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(sentence, wav_file)

    buffer.seek(0)
    samples, samplerate = sf.read(buffer, dtype="float32")

    return samples, samplerate


def synthesize_wav_piper(text, out_path, gap=0.25, tail=0.25):
    sentences = split_sentences(text)

    if not sentences:
        raise ValueError("Пустой текст")

    chunks = []
    samplerate = None

    for index, sentence in enumerate(sentences):
        samples, rate = synthesize_sentence(sentence)

        if samplerate is None:
            samplerate = rate
        elif rate != samplerate:
            raise ValueError("Разная частота дискретизации: {0} и {1}".format(
                samplerate, rate
            ))

        chunks.append(samples)

        is_last = index == len(sentences) - 1
        pause = tail if is_last else gap
        chunks.append(np.zeros(int(samplerate * pause), dtype="float32"))

    audio = np.concatenate(chunks)

    sf.write(str(out_path), audio, samplerate, subtype="PCM_16")


def play_wav(path):
    data, fs = sf.read(str(path), dtype="float32")
    sd.play(data, fs)
    sd.wait()


if __name__ == "__main__":
    out = "test.wav"

    text = (
        "Проверка связи, сэр. "
        "Системы работают штатно. "
        "Последняя запись сохранена."
    )

    synthesize_wav_piper(text, out)
    play_wav(out)