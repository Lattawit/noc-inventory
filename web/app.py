import os
import ipaddress
import subprocess
from datetime import datetime

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


def ping(ip):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "1", ip],
                           capture_output=True, timeout=3)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def validate(f, device_id=None):
    errors = []
    ip = f["ip_address"]
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        errors.append(f"'{ip}' is not a valid IP address.")
    else:
        dup = query(
            "SELECT hostname FROM devices WHERE ip_address=%s AND id IS DISTINCT FROM %s",
            (ip, device_id),
        )
        if dup:
            errors.append(f"IP {ip} is already used by {dup[0]['hostname']}.")
    vlan = f.get("vlan", "").strip()
    if vlan and not (vlan.isdigit() and 1 <= int(vlan) <= 4094):
        errors.append("VLAN must be a number between 1 and 4094.")
    return errors


def form_to_device(f):
    d = dict(f)
    d["location_id"] = int(d["location_id"]) if d.get("location_id") else None
    return d


@app.route("/")
def index():
    status = request.args.get("status", "all")
    q = request.args.get("q", "").strip()

    sql = """SELECT d.*, l.name AS location_name
             FROM devices d
             LEFT JOIN locations l ON d.location_id = l.id
             WHERE 1=1"""
    params = []
    if status in ("up", "down"):
        sql += " AND d.status = %s"
        params.append(status)
    if q:
        sql += """ AND (d.hostname ILIKE %s OR d.ip_address ILIKE %s
                        OR d.vendor ILIKE %s OR l.name ILIKE %s)"""
        params += [f"%{q}%"] * 4
    sql += " ORDER BY d.id"

    devices = query(sql, params)
    totals = query("""SELECT COUNT(*) AS total,
                             COUNT(*) FILTER (WHERE status='up') AS up
                      FROM devices""")[0]
    return render_template("index.html", devices=devices, total=totals["total"],
                           up=totals["up"], status=status, q=q)


@app.route("/add", methods=["GET", "POST"])
def add():
    locations = query("SELECT * FROM locations ORDER BY name")
    if request.method == "POST":
        f = request.form.to_dict()
        f["ip_address"] = f["ip_address"].strip()
        errors = validate(f)
        if errors:
            return render_template("form.html", device=form_to_device(f),
                                   locations=locations, types=DEVICE_TYPES,
                                   errors=errors, editing=False)
        query(
            """INSERT INTO devices
               (hostname, ip_address, device_type, vendor, vlan, status, location_id, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (f["hostname"], f["ip_address"], f["device_type"], f["vendor"],
             f["vlan"] or None, f["status"], f["location_id"] or None, f["notes"]),
            fetch=False,
        )
        return redirect(url_for("index"))
    return render_template("form.html", device=None, locations=locations,
                           types=DEVICE_TYPES, errors=[], editing=False)


@app.route("/edit/<int:device_id>", methods=["GET", "POST"])
def edit(device_id):
    locations = query("SELECT * FROM locations ORDER BY name")
    if request.method == "POST":
        f = request.form.to_dict()
        f["ip_address"] = f["ip_address"].strip()
        errors = validate(f, device_id)
        if errors:
            return render_template("form.html", device=form_to_device(f),
                                   locations=locations, types=DEVICE_TYPES,
                                   errors=errors, editing=True)
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
    return render_template("form.html", device=rows[0], locations=locations,
                           types=DEVICE_TYPES, errors=[], editing=True)


@app.route("/delete/<int:device_id>", methods=["POST"])
def delete(device_id):
    query("DELETE FROM devices WHERE id=%s", (device_id,), fetch=False)
    return redirect(url_for("index"))


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