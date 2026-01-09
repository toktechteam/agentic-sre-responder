import os

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "optional_dependency": os.environ.get("OPTIONAL_DEPENDENCY", "disabled"),
        }
    )


@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True) or {}
    return jsonify(
        {
            "model": "app-b",
            "input": payload,
            "optional_dependency": os.environ.get("OPTIONAL_DEPENDENCY", "disabled"),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
