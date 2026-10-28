import sqlite3
import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/reports/<team>")
def team_report(team):
    conn = sqlite3.connect("reports.db")
    sql = "SELECT day, total FROM sales WHERE team = '" + team + "' ORDER BY day"
    rows = conn.execute(sql).fetchall()  # @label sql_injection critical
    conn.close()
    return jsonify([list(r) for r in rows])


@app.route("/reports/archive", methods=["POST"])
def archive_reports():
    name = request.form["name"]
    subprocess.run("tar czf /tmp/%s.tgz reports/" % name, shell=True, check=True)  # @label command_injection critical
    return jsonify(archive=f"/tmp/{name}.tgz")
