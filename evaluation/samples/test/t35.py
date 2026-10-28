import os

from flask import Flask, abort, request, send_file

app = Flask(__name__)
EXPORT_DIR = "/srv/exports"


@app.route("/exports/download")
def download_export():
    name = request.args.get("name")
    if not name or not name.endswith(".csv"):
        abort(400)
    path = os.path.join(EXPORT_DIR, name)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True)
