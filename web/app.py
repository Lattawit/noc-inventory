import os
import psycopg2
import psycopg2.extras
import subprocess
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

DEVICE_TYPES = ["Router", "Switch", "Firewall", "Access Point", "Server"]


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def query(sql, params=None, fetch=True):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()


@app.route("/")
def index():
    devices = query("""
        SELECT d.*, l.name AS location_name
        FROM devices d
        LEFT JOIN locations l ON d.location_id = l.id
        ORDER BY d.id
    """)
    return render_template("index.html", devices=devices)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        f = request.form
        query(
            """INSERT INTO devices
               (hostname, ip_address, device_type, vendor, vlan, status, location_id, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (f["hostname"], f["ip_address"], f["device_type"], f["vendor"],
             f["vlan"] or None, f["status"], f["location_id"] or None, f["notes"]),
            fetch=False,
        )
        return redirect(url_for("index"))
    locations = query("SELECT * FROM locations ORDER BY name")
    return render_template("form.html", device=None, locations=locations,
                           types=DEVICE_TYPES)


@app.route("/edit/<int:device_id>", methods=["GET", "POST"])
def edit(device_id):
    if request.method == "POST":
        f = request.form
        query(
            """UPDATE devices SET hostname=%s, ip_address=%s, device_type=%s,
               vendor=%s, vlan=%s, status=%s, location_id=%s, notes=%s
               WHERE id=%s""",
            (f["hostname"], f["ip_address"], f["device_type"], f["vendor"],
             f["vlan"] or None, f["status"], f["location_id"] or None,
             f["notes"], device_id),
            fetch=False,
        )
        return redirect(url_for("index"))
    rows = query("SELECT * FROM devices WHERE id=%s", (device_id,))
    if not rows:
        return redirect(url_for("index"))
    locations = query("SELECT * FROM locations ORDER BY name")
    return render_template("form.html", device=rows[0], locations=locations,
                           types=DEVICE_TYPES)


@app.route("/delete/<int:device_id>", methods=["POST"])
def delete(device_id):
    query("DELETE FROM devices WHERE id=%s", (device_id,), fetch=False)
    return redirect(url_for("index"))

import subprocess
from datetime import datetime


def ping(ip):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                           capture_output=True, timeout=3)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


@app.route("/check/<int:device_id>", methods=["POST"])
def check(device_id):
    rows = query("SELECT ip_address FROM devices WHERE id=%s", (device_id,))
    if rows:
        status = "up" if ping(rows[0]["ip_address"]) else "down"
        query("UPDATE devices SET status=%s, last_checked=%s WHERE id=%s",
              (status, datetime.now(), device_id), fetch=False)
    return redirect(url_for("index"))


@app.route("/check-all", methods=["POST"])
def check_all():
    for d in query("SELECT id, ip_address FROM devices"):
        status = "up" if ping(d["ip_address"]) else "down"
        query("UPDATE devices SET status=%s, last_checked=%s WHERE id=%s",
              (status, datetime.now(), d["id"]), fetch=False)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)