from flask import Flask, request, jsonify, send_file
from pathlib import Path
import json

app = Flask(__name__)

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
REGISTRY_PATH = Path(__file__).parent / "modules_registry.json"


@app.route("/api/speak_audio", methods=["POST"])
def speak_audio():
    data = request.get_json(silent=True) or {}
    filename = data.get("file_name", "")
    path = AUDIO_DIR / filename

    if not path.exists():
        return jsonify({"success": False, "error": "File not found"}), 404

    url = f"http://{request.host}/audio/{filename}"
    return jsonify({"success": True, "url": url})


@app.route("/audio/<filename>", methods=["GET"])
def get_audio(filename):
    path = AUDIO_DIR / filename
    if not path.exists():
        return "Not found", 404
    return send_file(path, mimetype="audio/wav")


@app.route("/api/test", methods=["GET"])
def test_endpoint():
    return jsonify({
        "status": "ok",
        "message": "Мозг работает!"
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_text = data.get("text", "")

    response_text = "Это тестовый ответ от мозга."

    return jsonify({
        "success": True,
        "response": response_text,
        "request_text": user_text,
    })


@app.route("/api/modules", methods=["POST"])
def add_module():
    data = request.get_json(silent=True) or {}

    required = ["module_id", "module_type", "status", "tools"]
    if not all(k in data for k in required):
        return jsonify({
            "success": False,
            "error": "Missing required fields: module_id, module_type, status, tools"
        }), 400

    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        registry = json.load(f)

    if any(m["module_id"] == data["module_id"] for m in registry):
        return jsonify({
            "success": False,
            "error": f"Module {data['module_id']} already exists"
        }), 409

    registry.append(data)

    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    return jsonify({"success": True})


if __name__ == "__main__":
    print("Запуск тестового мозга...")
    app.run(host="0.0.0.0", port=5000, debug=True)
