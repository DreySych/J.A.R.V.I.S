from pathlib import Path
from datetime import datetime
from time import sleep
import sqlite3

from flask import Flask, request, jsonify, send_file
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from libcamera import Transform


# Сервер и папки с файлами рядом с camera.py.
app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
PHOTO_DIR = BASE_DIR / "media" / "photos"
VIDEO_DIR = BASE_DIR / "media" / "videos"
DATABASE_PATH = BASE_DIR / "database.db"

PHOTO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# Камеру используем по очереди для фото и видео.
camera = Picamera2()
video_recording = False
current_video_path = None


def init_db():
    # В базе храним сведения о файлах, а сами файлы — в папках.
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    # Счётчики сохраняются при перезапуске и не сбрасываются при удалении.
    connection.execute("""
        CREATE TABLE IF NOT EXISTS name_counters (
            type TEXT PRIMARY KEY,
            last_number INTEGER NOT NULL
        )
    """)
    connection.commit()
    connection.close()


def get_auto_name(media_type):
    # Создаём photo1, photo2... или video1, video2... без скобок.
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.execute(
        "SELECT last_number FROM name_counters WHERE type = ?",
        (media_type,)
    )
    row = cursor.fetchone()
    number = 0
    if row is not None:
        number = row[0]

    # Пропускаем имена, которые пользователь уже занял вручную.
    while True:
        number += 1
        name = media_type + str(number)
        cursor = connection.execute(
            "SELECT id FROM media WHERE name = ? AND type = ?",
            (name, media_type)
        )
        if cursor.fetchone() is None:
            break

    connection.execute(
        "INSERT OR REPLACE INTO name_counters (type, last_number) VALUES (?, ?)",
        (media_type, number)
    )
    connection.commit()
    connection.close()
    return name


def save_media_to_db(name, media_type, path):
    # Добавляем сведения о завершённом снимке или видео.
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        "INSERT INTO media (name, type, path, created_at) VALUES (?, ?, ?, ?)",
        (name, media_type, str(path), datetime.now().isoformat())
    )
    connection.commit()
    connection.close()


def find_media(name, media_type):
    # Если в старой базе есть дубликаты, выбираем последний.
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.execute(
        """
        SELECT id, name, type, path FROM media
        WHERE name = ? AND type = ?
        ORDER BY id DESC LIMIT 1
        """,
        (name, media_type)
    )
    row = cursor.fetchone()
    connection.close()
    return row


def find_last_media(media_type):
    # Находим последний добавленный файл выбранного типа.
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.execute(
        """
        SELECT id, name, type, path FROM media
        WHERE type = ?
        ORDER BY id DESC LIMIT 1
        """,
        (media_type,)
    )
    row = cursor.fetchone()
    connection.close()
    return row


def delete_media_record(row):
    # row содержит: id, name, type, path.
    # Сначала удаляем файл. При ошибке запись в базе останется.
    file_path = Path(row[3])
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return jsonify(result="error", message="Не удалось удалить файл"), 500

    # Если файла уже не было, тоже удаляем оставшуюся запись.
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("DELETE FROM media WHERE id = ?", (row[0],))
    connection.commit()
    connection.close()
    return jsonify(result="success")


@app.route("/capture_photo/", methods=["POST"])
def capture_photo():
    # Не фотографируем во время записи видео.
    if video_recording:
        return jsonify(result="error", message="Идёт запись видео"), 409

    # Можно отправить JSON с name, пустой объект или запрос без body.
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify(result="error", message="Body должен быть JSON-объектом"), 400
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        return jsonify(result="error", message="name должен быть строкой"), 400
    if name is not None:
        name = name.strip()
    if not name:
        name = get_auto_name("photo")

    # Два фото с одинаковым названием сохранять нельзя.
    if find_media(name, "photo") is not None:
        return jsonify(result="error", message="Название фото уже занято"), 409

    filename = datetime.now().strftime("photo_%Y%m%d_%H%M%S_%f.jpg")
    photo_path = PHOTO_DIR / filename

    # Включаем зеркальное отражение для самого сохранённого снимка.
    config = camera.create_still_configuration(transform=Transform(hflip=True))
    camera.configure(config)
    camera.start()
    try:
        sleep(2)
        camera.capture_file(str(photo_path))
    finally:
        camera.stop()

    save_media_to_db(name, "photo", photo_path)
    return jsonify(result="success", name=name)


@app.route("/start_video/", methods=["POST"])
def start_video():
    global video_recording, current_video_path

    if video_recording:
        return jsonify(result="error", message="Запись уже идёт"), 409

    # После конфликта названий сначала нужно назвать предыдущее видео.
    if current_video_path is not None:
        return jsonify(
            result="error",
            message="Сохраните предыдущее видео через /stop_video/ с другим названием"
        ), 409

    filename = datetime.now().strftime("video_%Y%m%d_%H%M%S_%f.mp4")
    video_path = VIDEO_DIR / filename

    # Записываем зеркальное видео без звука.
    config = camera.create_video_configuration(transform=Transform(hflip=True))
    camera.configure(config)
    encoder = H264Encoder()
    output = FfmpegOutput(str(video_path))
    camera.start_recording(encoder, output)

    # Picamera2 продолжает запись в фоне после ответа сервера.
    current_video_path = video_path
    video_recording = True
    return jsonify(result="success", status="recording")


@app.route("/video_status/", methods=["GET"])
def video_status():
    # Это состояние записи, а не проверка исправности оборудования.
    status = "stopped"
    if video_recording:
        status = "recording"
    return jsonify(status=status)


@app.route("/stop_video/", methods=["POST"])
def stop_video():
    global video_recording, current_video_path

    if not video_recording and current_video_path is None:
        return jsonify(result="error", message="Нет видео для сохранения"), 409

    # Название необязательно: без него назначаем video1, video2...
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify(result="error", message="Body должен быть JSON-объектом"), 400
    name = data.get("name")
    if name is not None and not isinstance(name, str):
        return jsonify(result="error", message="name должен быть строкой"), 400
    if name is not None:
        name = name.strip()
    if not name:
        name = get_auto_name("video")

    # Останавливаем запись только при первом запросе.
    if video_recording:
        camera.stop_recording()
        video_recording = False

    # Видео уже записано. При конфликте ждём запроса с новым названием.
    if find_media(name, "video") is not None:
        return jsonify(
            result="error",
            status="stopped",
            message="Видео записано, но название занято. Повторите /stop_video/ с другим названием"
        ), 409

    save_media_to_db(name, "video", current_video_path)
    current_video_path = None
    return jsonify(result="success", name=name)


@app.route("/get_media/", methods=["POST"])
def get_media():
    # Название и тип передаём в body, без параметров в URL.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(result="error", message="Отправьте JSON с name и type"), 400
    media_type = data.get("type")
    name = data.get("name")
    if media_type not in ("photo", "video"):
        return jsonify(result="error", message="type должен быть photo или video"), 400
    if not isinstance(name, str) or not name.strip():
        return jsonify(result="error", message="Укажите name"), 400

    row = find_media(name.strip(), media_type)
    if row is None or not Path(row[3]).is_file():
        return jsonify(result="error", message="Контент не найден"), 404

    mimetype = "image/jpeg"
    extension = ".jpg"
    if media_type == "video":
        mimetype = "video/mp4"
        extension = ".mp4"

    # При скачивании показываем название из базы, а не служебную дату.
    return send_file(
        row[3], mimetype=mimetype, as_attachment=True,
        download_name=row[1] + extension
    )


@app.route("/delete_media/", methods=["DELETE"])
def delete_media():
    # Тип обязателен, название можно не указывать.
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(result="error", message="Отправьте JSON с type"), 400
    name = data.get("name")
    media_type = data.get("type")
    if media_type not in ("photo", "video"):
        return jsonify(result="error", message="type должен быть photo или video"), 400
    if name is not None and not isinstance(name, str):
        return jsonify(result="error", message="name должен быть строкой"), 400
    if name is not None:
        name = name.strip()

    # С названием удаляем выбранный файл, без названия — последний по типу.
    if name:
        row = find_media(name, media_type)
    else:
        row = find_last_media(media_type)
    if row is None:
        return jsonify(result="error", message="Контент не найден"), 404
    return delete_media_record(row)


@app.route("/list_media/", methods=["GET"])
def list_media():
    # Берём названия, типы и даты из базы. Последние записи идут первыми.
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.execute("""
        SELECT name, type, created_at
        FROM media
        WHERE type IN ('photo', 'video')
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    connection.close()

    # Собираем обычный текст, который Postman покажет в Body ответа.
    lines = ["Сохранённые фото и видео", ""]
    for name, media_type, created_at in rows:
        date = datetime.fromisoformat(created_at)
        date = date.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(
            f"Тип: {media_type} | Название: {name} | Создано: {date}"
        )

    if not rows:
        lines.append("Сохранённых фото и видео пока нет.")

    # Возвращаем сам текст без ссылки и без принудительного скачивания файла.
    text = "\n".join(lines)
    return app.response_class(text, content_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    init_db()
    try:
        # Один процесс и последовательная обработка запросов:
        # проверка названия и сохранение не мешают друг другу.
        # Запись видео работает отдельно средствами Picamera2.
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=False)
    finally:
        camera.close()
