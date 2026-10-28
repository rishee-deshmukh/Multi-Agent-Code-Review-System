import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/diagnostics/dns")
def dns_lookup():
    host = request.args.get("host", "")
    if len(host) > 253:
        return jsonify(error="hostname too long"), 400
    result = subprocess.run(  # @label command_injection critical
        f"nslookup {host}", shell=True, capture_output=True, text=True, timeout=5
    )
    return jsonify(output=result.stdout, returncode=result.returncode)
