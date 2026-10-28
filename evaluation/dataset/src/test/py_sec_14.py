from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")


if __name__ == "__main__":
    app.run(port=8080, debug=True)  # @label debug_enabled medium -- Werkzeug debugger allows code execution
