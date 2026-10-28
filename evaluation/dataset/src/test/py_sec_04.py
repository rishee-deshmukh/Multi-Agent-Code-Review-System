from flask import Flask, jsonify, request

app = Flask(__name__)

NOTIFICATIONS = {"alice": 3, "bob": 0}


@app.route("/api/unread/<user>")
def unread(user):
    return jsonify(count=NOTIFICATIONS.get(user, 0))


@app.route("/welcome")
def welcome():
    name = request.args.get("name", "guest")
    unread_count = NOTIFICATIONS.get(name, 0)
    return f"<html><body><h1>Welcome back, {name}!</h1><p>{unread_count} unread</p></body></html>"  # @label xss high
