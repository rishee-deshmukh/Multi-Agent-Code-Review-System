import os
from urllib.parse import urlparse

import requests
from flask import Flask, abort, jsonify, request

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = {"api.example.com", "cdn.example.com"}


@app.route("/link-preview")
def link_preview():
    parsed = urlparse(request.args.get("url", ""))
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        abort(400)
    resp = requests.get(parsed.geturl(), timeout=5, allow_redirects=False)
    return jsonify(status=resp.status_code, size=len(resp.content))
