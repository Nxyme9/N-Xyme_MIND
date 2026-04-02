from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/echo', methods=['POST'])
def echo():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Missing message"}), 400
    return jsonify(data), 200

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    if not data or 'a' not in data or 'b' not in data:
        return jsonify({"error": "Missing a or b"}), 400
    try:
        a = float(data['a'])
        b = float(data['b'])
        result = a + b
        return jsonify({"result": result}), 200
    except ValueError:
        return jsonify({"error": "Invalid numbers"}), 400

if __name__ == '__main__':
    app.run(debug=True)
