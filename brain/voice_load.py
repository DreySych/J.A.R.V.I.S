import torch
import soundfile as sf
import sounddevice as sd
import librosa

device = torch.device("cpu")

tts_model, example_text = torch.hub.load(
    "snakers4/silero-models",
    "silero_tts",
    language="ru",
    speaker="v4_ru",
)

tts_model.to(device)


def synthesize_wav_silero(text, out_path, semitones=4.0):
    audio = tts_model.apply_tts(
        text=text,
        speaker="eugene",
        sample_rate=48000,
    )

    samples = audio.detach().cpu().numpy().squeeze()

    if semitones:
        samples = librosa.effects.pitch_shift(
            samples, sr=48000, n_steps=semitones
        )

    sf.write(
        out_path,
        samples,
        48000,
        subtype="PCM_16",
        format="WAV",
    )

if __name__ == "__main__":
    synthesize_wav_silero("Проверка связи", "test.wav", semitones=4.0)
    data, fs = sf.read("test.wav", dtype="float32")
    sd.play(data, fs)
    sd.wait()