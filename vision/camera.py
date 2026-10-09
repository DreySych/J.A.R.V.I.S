from pathlib import Path
from datetime import datetime
import sqlite3
import threading

import cv2
from flask import Flask, request, jsonify, send_file, send_from_directory, Response


app = Flask(__name__) #приложение

#создание путей для папок
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
PHOTO_DIR = MEDIA_DIR / "camera_photos"
VIDEO_DIR = MEDIA_DIR / "camera_videos"
BOARD_DIR = MEDIA_DIR / "board_photos"
DATABASE_PATH = BASE_DIR / "database.db"


#создаем сами папки если их нет
PHOTO_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
BOARD_DIR.mkdir(parents=True, exist_ok=True)


#обьявляем глобальные переменные с сотоянием стрима , видео и тд
stream_active = False
video_recording = False
video_thread = None
current_video_name = None
last_video_info = None


def init_db():
    #открываем базу данных и создаём таблицу для сведений о файлах
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

    # Подтверждаем изменения и закрываем соединение с базой.
    connection.commit()
    connection.close()


def save_media_to_db(name, media_type, path):
    # добавляем в базу название, тип, путь к файлу и текущее время.
    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.execute(
        "INSERT INTO media (name, type, path, created_at) VALUES (?, ?, ?, ?)",
        (name, media_type, path, datetime.now().isoformat())
    )

    # получаем номер новой записи, сохраняем её и возвращаем номер.
    media_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return media_id


def capture_frame():
    #открываем первую камеру, получаем один кадр и освобождаем камеру.
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    success, frame = camera.read()
    camera.release()

    #если получить кадр не удалось, возвращаем отсутствие результата.
    if not success:
        return None

    return cv2.flip(frame, 1)


@app.route("/capture_photo/", methods=["POST"])
def capture_photo():
    #получаем JSON из запроса и делаем снимок камерой.
    data = request.get_json()
    frame = capture_frame()

    #если камера не выдала кадр, возвращаем ошибку.
    if frame is None:
        return jsonify(result="error"), 500

    #создаём имя по дате и времени, затем сохраняем кадр как JPEG.
    filename = datetime.now().strftime("photo_%Y%m%d_%H%M%S_%f.jpg")
    file_path = PHOTO_DIR / filename
    cv2.imwrite(str(file_path), frame)

    #сохраняем сведения о фотографии в базе данных.
    save_media_to_db(
        data.get("name"),
        "camera_photo",
        "camera_photos/" + filename
    )

    #отправляем клиенту сохранённое изображение.
    return send_file(file_path, mimetype="image/jpeg")


def generate_stream():
    #используем глобальную переменную состояния и открываем камеру.
    global stream_active
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # получаем кадры и по одному отправляем их клиенту,
    # пока трансляция включена.
    try:
        while stream_active:
            #получаем очередной кадр. При неудаче заканчиваем цикл.
            success, frame = camera.read()

            if not success:
                break

            #отражаем кадр и преобразуем его в JPEG в памяти.
            frame = cv2.flip(frame, 1)
            success, jpeg = cv2.imencode(".jpg", frame)

            #если преобразование не удалось, переходим к следующему кадру.
            if not success:
                continue

            #отдаём один JPEG-кадр с разделителем и HTTP-заголовком.
            #yield позволяет затем продолжить и отдать следующий кадр.
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg.tobytes()
                + b"\r\n"
            )

    # При завершении трансляции освобождаем камеру и сбрасываем состояние.
    finally:
        camera.release()
        stream_active = False


@app.route("/stream_camera/", methods=["GET"])
def stream_camera():
    # Включаем трансляцию.
    global stream_active
    stream_active = True

    # Возвращаем HTTP-ответ, в который постепенно поступают JPEG-кадры.
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/stop_stream/", methods=["POST"])
def stop_stream():
    # Даём циклу трансляции команду завершиться.
    global stream_active
    stream_active = False

    # Сообщаем клиенту, что команда остановки принята.
    return jsonify(result="success", status="stopped")


@app.route("/stream_status/", methods=["GET"])
def stream_status():
    # Определяем состояние трансляции по общей переменной.
    status = "stopped"

    if stream_active:
        status = "streaming"

    # Возвращаем состояние в формате JSON.
    return jsonify(status=status)


def record_video(video_name):
    # Используем общие переменные и открываем камеру.
    global video_recording, last_video_info
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    # Получаем размер кадра и частоту кадров камеры.
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = camera.get(cv2.CAP_PROP_FPS)

    # Если камера не сообщила положительный FPS, используем 20.
    if fps <= 0:
        fps = 20

    # Создаём имя файла и объект, который будет записывать видео.
    filename = datetime.now().strftime("video_%Y%m%d_%H%M%S_%f.mp4")
    file_path = VIDEO_DIR / filename
    codec = cv2.VideoWriter_fourcc("m", "p", "4", "v")
    writer = cv2.VideoWriter(str(file_path), codec, fps, (width, height))

    # Получаем, отражаем и записываем кадры, пока запись включена.
    while video_recording:
        success, frame = camera.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)
        writer.write(frame)

    # Завершаем видеофайл и освобождаем камеру.
    writer.release()
    camera.release()

    # Добавляем сведения о записанном видео в базу данных.
    relative_path = "camera_videos/" + filename
    media_id = save_media_to_db(video_name, "camera_video", relative_path)

    # Сохраняем результат, чтобы эндпоинт остановки мог вернуть его клиенту.
    last_video_info = {
        "id": media_id,
        "name": video_name,
        "path": relative_path
    }

    # Отмечаем, что запись закончилась.
    video_recording = False


@app.route("/start_video/", methods=["POST"])
def start_video():
    # Разрешаем функции менять общие переменные записи.
    global video_recording, video_thread
    global current_video_name, last_video_info

    # Не запускаем ещё одну запись, если предыдущая уже идёт.
    if video_recording:
        return jsonify(result="error", message="Запись уже идёт"), 409

    # Получаем название видео и подготавливаем состояние новой записи.
    data = request.get_json()
    current_video_name = data.get("name")
    last_video_info = None
    video_recording = True

    # Запускаем запись отдельно, чтобы сервер мог принимать другие запросы.
    video_thread = threading.Thread(
        target=record_video,
        args=(current_video_name,)
    )
    video_thread.start()

    # Сообщаем клиенту о запуске записи.
    return jsonify(
        result="success",
        status="recording",
        name=current_video_name
    )


@app.route("/video_status/", methods=["GET"])
def video_status():
    # Определяем состояние записи по общей переменной.
    status = "stopped"

    if video_recording:
        status = "recording"

    # Возвращаем состояние и название видео.
    return jsonify(status=status, name=current_video_name)


@app.route("/stop_video/", methods=["POST"])
def stop_video():
    global video_recording

    # Если запись не идёт, сообщаем об этом клиенту.
    if not video_recording:
        return jsonify(result="error", message="Запись не идёт"), 409

    # Останавливаем цикл записи и ждём завершения сохранения видео.
    video_recording = False
    video_thread.join()

    # Возвращаем сведения о сохранённом видео.
    return jsonify(
        result="success",
        status="stopped",
        video=last_video_info
    )


@app.route("/set_board_photo/", methods=["POST"])
def set_board_photo():
    # Получаем загруженный файл из поля формы с названием file.
    file = request.files["file"]

    # Создаём имя и сохраняем полученный файл в папку доски.
    filename = datetime.now().strftime("board_%Y%m%d_%H%M%S_%f.jpg")
    file.save(BOARD_DIR / filename)

    # Добавляем сведения о картинке в базу данных.
    save_media_to_db(
        file.filename,
        "board_photo",
        "board_photos/" + filename
    )

    # Подтверждаем загрузку.
    return jsonify(result="success")


@app.route("/media/<path:filename>", methods=["GET"])
def get_media(filename):
    # Отправляем клиенту запрошенный файл из папки media.
    return send_from_directory(MEDIA_DIR, filename)


@app.route("/board/", methods=["GET"])
def board():
    # Находим в базе последнюю загруженную картинку для доски.
    connection = sqlite3.connect(DATABASE_PATH)

    cursor = connection.execute("""
        SELECT path FROM media
        WHERE type = 'board_photo'
        ORDER BY id DESC
        LIMIT 1
    """)

    # Получаем найденную запись и закрываем соединение.
    row = cursor.fetchone()
    connection.close()

    # Если картинок ещё нет, показываем текст.
    if row is None:
        return "Фото пока не загружено"

    # Возвращаем страницу, которая показывает картинку на чёрном фоне.
    # Браузер получает само изображение через эндпоинт /media/.
    return f"""
    <html>
        <body style="background: black; margin: 0; display: flex;
                     justify-content: center; align-items: center;
                     height: 100vh;">
            <img src="/media/{row[0]}"
                 style="max-width: 100%; max-height: 100%;">
        </body>
    </html>
    """


# При прямом запуске файла подготавливаем базу и запускаем сервер.
# threaded=True позволяет обрабатывать запросы во время трансляции.
if __name__ == "__main__":
    init_db()
    app.run(debug=False, threaded=True)