import torch
import soundfile as sf

device = torch.device("cpu")

tts_model, example_text = torch.hub.load(
    "snakers4/silero-models",
    "silero_tts",
    language="ru",
    speaker="v4_ru",
)

tts_model.to(device)


def synthesize_wav(text, out_path):
    audio = tts_model.apply_tts(
        text=text,
        speaker="eugene",
        sample_rate=48000,
    )

    sf.write(
        out_path,
        audio.detach().cpu().numpy(),
        48000,
        subtype="PCM_16",
        format="WAV",
    )
