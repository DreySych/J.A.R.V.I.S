from flask import Flask, jsonify
import cv2
import base64

app = Flask(__name__)


def photo_camera():
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not camera.isOpened():
        return None

    success, frame = camera.read()
    camera.release()

    if not success:
        return None

    return frame


@app.route('/take_photo_camera/', methods=['POST'])
def take_photo_camera():
    frame = photo_camera()

    if frame is None:
        return jsonify({
            "result": "error"
        }), 500

    success, buffer = cv2.imencode('.jpg', frame)

    if not success:
        return jsonify({
            "result": "error"
        }), 500

    photo_base64 = base64.b64encode(buffer).decode('utf-8')

    return jsonify({
        "result": "success",
        "photo": photo_base64
    })


if __name__ == '__main__':
    app.run(debug=True)