import base64
import pickle

from flask import Flask, jsonify, request

app = Flask(__name__)


def load_preferences():
    cookie = request.cookies.get("prefs")
    if not cookie:
        return {"theme": "light"}
    return pickle.loads(base64.b64decode(cookie))  # @label deserialization critical


@app.route("/settings")
def settings():
    prefs = load_preferences()
    return jsonify(theme=prefs.get("theme", "light"))
