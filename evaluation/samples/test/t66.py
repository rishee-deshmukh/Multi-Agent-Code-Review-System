from flask import Flask, render_template_string, request

app = Flask(__name__)

HEADER = "<h1>Order confirmation</h1>"


def format_total(cents):
    return f"{cents / 100:.2f}"


@app.route("/confirmation")
def confirmation():
    note = request.args.get("note", "")
    total = format_total(int(request.args.get("cents", 0)))
    template = HEADER + "<p>Note: " + note + "</p><p>Total: " + total + "</p>"
    return render_template_string(template)
