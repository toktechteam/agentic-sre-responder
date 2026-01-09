import os
import sys
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

REQUIRED_ENV = "APP_A_REQUIRED"


def _require_env() -> None:
    if not os.environ.get(REQUIRED_ENV):
        print(f"missing required env: {REQUIRED_ENV}", flush=True)
        sys.exit(1)


@app.route("/health", methods=["GET"])
def health():
    latency_mode = os.environ.get("LATENCY_MODE", "off")
    if latency_mode == "on":
        time.sleep(3)
    return jsonify({"status": "ok", "latency_mode": latency_mode})


@app.route("/predict", methods=["POST"])
def predict():
    latency_mode = os.environ.get("LATENCY_MODE", "off")
    if latency_mode == "on":
        time.sleep(3)
    payload = request.get_json(silent=True) or {}
    return jsonify({"model": "app-a", "input": payload, "latency_mode": latency_mode})


if __name__ == "__main__":
    _require_env()
    app.run(host="0.0.0.0", port=8080)
