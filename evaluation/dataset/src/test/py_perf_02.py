import sqlite3


def load_dashboards(conn: sqlite3.Connection, user_ids):
    dashboards = []
    for uid in user_ids:
        user = conn.execute("SELECT id, name FROM users WHERE id = ?", (uid,)).fetchone()  # @label io_in_loop high -- N+1 queries
        orders = conn.execute("SELECT id, total FROM orders WHERE user_id = ?", (uid,)).fetchall()
        dashboards.append({"user": user, "orders": orders})
    return dashboards
