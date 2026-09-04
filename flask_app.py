from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return "Бот работает! 🚀"
    
    data = request.get_json()
    if data and data.get('type') == 'confirmation':
        return os.getenv("CONFIRMATION_TOKEN", "fbe8394f")
    
    return "ok"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
