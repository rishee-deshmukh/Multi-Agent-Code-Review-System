import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/products/search")
def search_products():
    term = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 20)), 100)
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY name LIMIT ?",
        (f"%{term}%", limit),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
