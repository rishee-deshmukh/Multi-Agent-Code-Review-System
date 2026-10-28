import os

from flask import Flask, redirect, request

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


def log_login(user):
    app.logger.info("login ok for %s", user)


@app.route("/auth/done")
def auth_done():
    log_login(request.args.get("uid", "unknown"))
    next_url = request.args.get("next", "/")
    return redirect(next_url)
