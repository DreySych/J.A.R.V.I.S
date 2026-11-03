from pathlib import Path
import zipfile
import requests

BASE_DIR = Path(__file__).resolve().parent
PIPER_DIR = BASE_DIR / "models" / "piper"
PIPER_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "ru_RU-ruslan-medium.onnx": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        "ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx?download=true"
    ),
    "ru_RU-ruslan-medium.onnx.json": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
        "ru/ru_RU/ruslan/medium/ru_RU-ruslan-medium.onnx.json?download=true"
    ),
}


def download_model(filename, url):
    destination = PIPER_DIR / filename

    if destination.exists():
        print(f"Уже скачано: {destination}")
        return

    print(f"Скачиваю: {filename}")

    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()

        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                file.write(chunk)

    print(f"Готово: {destination}")


if __name__ == "__main__":
    for filename, url in FILES.items():
        download_model(filename, url)

    vosk_dir = BASE_DIR / "models" / "vosk"
    model_name = "vosk-model-small-ru-0.22"

    if not (vosk_dir / model_name).exists():
        vosk_dir.mkdir(parents=True, exist_ok=True)
        archive_path = vosk_dir / f"{model_name}.zip"

        print("Скачиваю Vosk...")
        response = requests.get(
            f"https://alphacephei.com/vosk/models/{model_name}.zip",
            timeout=120,
        )
        response.raise_for_status()
        archive_path.write_bytes(response.content)

        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(vosk_dir)

        archive_path.unlink()
        print("Vosk готов!")
    else:
        print("Vosk уже скачан")
