import torch
import torchaudio

device = torch.device("cpu")

tts_model, example_text = torch.hub.load(
    "snakers4/silero-models",
    "silero_tts",
    language="ru",
    speaker="v4_ru",
)

tts_model.to(device)


def synthesize_wav(text: str, out_path: str):
    audio = tts_model.apply_tts(
        text=text,
        speaker="aidar",
        sample_rate=48000,
    )

    audio = audio.unsqueeze(0)

    torchaudio.save(out_path, audio, 48000)
