import hashlib
import html
import secrets

import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)


def file_checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pipeline(raw_text):
    return yaml.safe_load(raw_text)


@app.route("/welcome")
def welcome():
    name = html.escape(request.args.get("name", "guest"))
    return f"<html><body><h1>Welcome back, {name}!</h1></body></html>"


@app.route("/tokens", methods=["POST"])
def new_token():
    return jsonify(token=secrets.token_urlsafe(32))
