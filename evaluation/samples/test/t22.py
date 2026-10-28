import os

from flask import Flask, abort, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
EXPORT_DIR = os.path.realpath("/srv/exports")


@app.route("/exports/download")
def download_export():
    name = secure_filename(request.args.get("name", ""))
    if not name.endswith(".csv"):
        abort(400)
    return send_from_directory(EXPORT_DIR, name, as_attachment=True)
