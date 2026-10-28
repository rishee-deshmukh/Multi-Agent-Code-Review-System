import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "inventory.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/products/search")
def search_products():
    term = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 20)), 100)
    conn = get_db()
    sql = f"SELECT id, name, price FROM products WHERE name LIKE '%{term}%' ORDER BY name LIMIT ?"
    rows = conn.execute(sql, (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
