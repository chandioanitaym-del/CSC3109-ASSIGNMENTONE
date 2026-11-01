import hashlib
import hmac
import json
import os
from functools import wraps

from flask import Flask, jsonify, request

app = Flask(__name__)
KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api_keys.json")

try:
    with open(KEYS_FILE) as f:
        KEY_HASHES = json.load(f)  # {consumer: sha256 hex of key}
except FileNotFoundError:
    raise SystemExit("api_keys.json not found. Run: python generate_keys.py")


def find_consumer(key):
    digest = hashlib.sha256(key.encode()).hexdigest()
    match = None
    for consumer, stored in KEY_HASHES.items():
        if hmac.compare_digest(digest, stored):  # constant-time compare
            match = consumer
    return match


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if not key:
            return jsonify(error="Missing API key. Send it in the X-API-Key header."), 401
        consumer = find_consumer(key)
        if consumer is None:
            return jsonify(error="Invalid API key."), 403
        request.consumer = consumer
        return fn(*args, **kwargs)

    return wrapper


MODES = {
    "upper": str.upper,
    "lower": str.lower,
    "title": str.title,
    "reverse": lambda s: s[::-1],
}


@app.post("/process")
@require_api_key
def process():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return jsonify(error="JSON body with a string 'text' field is required"), 400
    mode = data.get("mode", "upper")
    if mode not in MODES:
        return jsonify(error=f"mode must be one of {list(MODES)}"), 400
    return jsonify(
        consumer=request.consumer,
        mode=mode,
        original=data["text"],
        processed=MODES[mode](data["text"]),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
