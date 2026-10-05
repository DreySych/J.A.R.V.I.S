from pathlib import Path
from datetime import datetime
import sqlite3
import threading

import cv2

from flask import (
    Flask,
    request,
    jsonify,
    send_file,
    send_from_directory,
    Response
)

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

MEDIA_DIR = BASE_DIR / "media"
CAMERA_PHOTOS_DIR = MEDIA_DIR / "camera_photos"
CAMERA_VIDEOS_DIR = MEDIA_DIR / "camera_videos"
BOARD_PHOTOS_DIR = MEDIA_DIR / "board_photos"

DATABASE_PATH = BASE_DIR / "database.db"

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
CAMERA_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
CAMERA_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
BOARD_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

video_recording = False
video_thread = None
current_video_name = None
last_video_info = None

stream_active = False


def init_db():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT NOT NULL,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_media_to_db(name, media_type, path):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO media (name, type, path, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            media_type,
            path,
            datetime.now().isoformat()
        )
    )

    media_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return media_id


def capture_frame():
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    success, frame = camera.read()

    camera.release()

    if not success:
        return None

    return frame


@app.route("/capture_photo/", methods=["POST"])
def capture_photo():
    data = request.json
    photo_name = data.get("name")

    frame = capture_frame()

    if frame is None:
        return jsonify({
            "result": "error"
        }), 500

    filename = datetime.now().strftime(
        "photo_%Y%m%d_%H%M%S.jpg"
    )

    file_path = CAMERA_PHOTOS_DIR / filename

    success, buffer = cv2.imencode(".jpg", frame)

    if not success:
        return jsonify({
            "result": "error"
        }), 500

    file_path.write_bytes(
        buffer.tobytes()
    )

    relative_path = f"camera_photos/{filename}"

    save_media_to_db(
        photo_name,
        "camera_photo",
        relative_path
    )

    return send_file(
        file_path,
        mimetype="image/jpeg"
    )


def generate_stream():
    global stream_active

    stream_active = True

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    while stream_active:
        success, frame = camera.read()

        if not success:
            break

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

    camera.release()
    stream_active = False


@app.route("/stream_camera/", methods=["GET"])
def stream_camera():
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/stop_stream/", methods=["POST"])
def stop_stream():
    global stream_active

    stream_active = False

    return jsonify({
        "result": "success",
        "status": "stopped"
    })


@app.route("/stream_status/", methods=["GET"])
def stream_status():
    if stream_active:
        status = "streaming"
    else:
        status = "stopped"

    return jsonify({
        "status": status
    })


def record_video(video_name):
    global video_recording
    global last_video_info

    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    width = int(
        camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    )

    height = int(
        camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )

    fps = camera.get(
        cv2.CAP_PROP_FPS
    )

    if fps <= 0:
        fps = 20

    filename = datetime.now().strftime(
        "video_%Y%m%d_%H%M%S.mp4"
    )

    file_path = CAMERA_VIDEOS_DIR / filename

    fourcc = cv2.VideoWriter_fourcc(
        *"mp4v"
    )

    writer = cv2.VideoWriter(
        str(file_path),
        fourcc,
        fps,
        (width, height)
    )

    while video_recording:
        success, frame = camera.read()

        if not success:
            break

        writer.write(frame)

    writer.release()
    camera.release()

    relative_path = f"camera_videos/{filename}"

    media_id = save_media_to_db(
        video_name,
        "camera_video",
        relative_path
    )

    last_video_info = {
        "id": media_id,
        "name": video_name,
        "path": relative_path
    }


@app.route("/start_video/", methods=["POST"])
def start_video():
    global video_recording
    global video_thread
    global current_video_name
    global last_video_info

    if video_recording:
        return jsonify({
            "result": "error",
            "message": "Video is already recording"
        }), 409

    data = request.json

    current_video_name = data.get("name")
    last_video_info = None

    video_recording = True

    video_thread = threading.Thread(
        target=record_video,
        args=(current_video_name,)
    )

    video_thread.start()

    return jsonify({
        "result": "success",
        "status": "recording",
        "name": current_video_name
    })


@app.route("/video_status/", methods=["GET"])
def video_status():
    if video_recording:
        status = "recording"
    else:
        status = "stopped"

    return jsonify({
        "status": status,
        "name": current_video_name
    })


@app.route("/stop_video/", methods=["POST"])
def stop_video():
    global video_recording
    global video_thread

    if not video_recording:
        return jsonify({
            "result": "error",
            "message": "Video is not recording"
        }), 409

    video_recording = False

    if video_thread is not None:
        video_thread.join()

    return jsonify({
        "result": "success",
        "status": "stopped",
        "video": last_video_info
    })

@app.route("/set_board_photo/", methods=["POST"])
def set_board_photo():
    file = request.files["file"]

    filename = datetime.now().strftime(
        "board_%Y%m%d_%H%M%S.jpg"
    )

    file_path = BOARD_PHOTOS_DIR / filename

    file.save(file_path)

    relative_path = f"board_photos/{filename}"

    save_media_to_db(
        file.filename,
        "board_photo",
        relative_path
    )

    return jsonify({
        "result": "success"
    })


@app.route("/media/<path:filename>", methods=["GET"])
def get_media(filename):
    return send_from_directory(
        MEDIA_DIR,
        filename
    )


@app.route("/board/", methods=["GET"])
def board():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT path
        FROM media
        WHERE type = 'board_photo'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return "Фото пока не загружено"

    current_photo = row[0]

    return f"""
    <html>
        <body style="
            background: black;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        ">
            <img
                src="/media/{current_photo}"
                style="
                    max-width: 100%;
                    max-height: 100%;
                "
            >
        </body>
    </html>
    """


if __name__ == "__main__":
    init_db()
    app.run(debug=True)