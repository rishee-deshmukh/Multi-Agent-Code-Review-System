import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/link-preview")
def link_preview():
    url = request.args.get("url", "")
    if not url.startswith("http"):
        return jsonify(error="only http(s) urls"), 400
    resp = requests.get(url, timeout=5)  # @label ssrf high -- scheme check only; internal hosts and cloud metadata are reachable
    return jsonify(status=resp.status_code, size=len(resp.content), type=resp.headers.get("Content-Type"))
