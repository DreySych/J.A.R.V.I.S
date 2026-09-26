from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/take_photo_camera/', methods=['POST'])
def take_photo_camera():
    return jsonify({
        "result": "success"
    })

if __name__ == '__main__':
    app.run(debug=True)