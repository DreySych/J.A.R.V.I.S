from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Реестр Speaker Node
speaker_nodes = []


# ==================== API ДЛЯ МОДУЛЕЙ ====================

@app.route('/api/module/register', methods=['POST'])
def register_module():
    """Регистрация модуля"""
    data = request.json
    module_id = data.get('module_id')
    module_type = data.get('module_type')

    if module_type == 'speaker':
        speaker_nodes.append(module_id)
        print(f"Зарегистрирован Speaker Node: {module_id}")

    return jsonify({
        "success": True,
        "message": f"Module {module_id} registered"
    })


@app.route('/api/audio', methods=['POST'])
def receive_audio():
    """Получает аудио от Speaker Node"""

    # Сохраняем аудио
    audio_file = request.files['audio']
    audio_data = audio_file.read()

    # Сохраняем в файл для проверки
    with open('recordings/test_audio.wav', 'wb') as f:
        f.write(audio_data)

    print(f"Получено аудио: {len(audio_data)} байт")

    # Возвращаем тестовый ответ
    return jsonify({
        "success": True,
        "text": "тестовая команда",
        "response": "Привет! Я получил твоё аудио."
    })


# ==================== ТЕСТИРОВАНИЕ ====================

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Тестовый endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Мозг работает!",
        "speaker_nodes": speaker_nodes
    })


if __name__ == '__main__':
    print("Запуск тестового мозга...")
    app.run(host='0.0.0.0', port=5000, debug=True)
