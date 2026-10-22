import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)