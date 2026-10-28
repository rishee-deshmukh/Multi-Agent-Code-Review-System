from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/calc")
def calc():
    expr = request.args.get("expr", "0")
    if len(expr) > 200:
        return jsonify(error="expression too long"), 400
    return jsonify(result=eval(expr))
