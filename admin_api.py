from flask import Flask, jsonify, request, abort, send_from_directory
import os
import sqlite3
import requests

BOT_TOKEN = "7975345597:AAH_CJ5aT8W_bZvfk5tCwgheDerncht5jvE"
ADMIN_ID = 5869177453

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

@app.route("/")
def home():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/index.html")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


def send_msg(uid, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": uid, "text": text}
    )

def db():
    return sqlite3.connect("orders.db")

def check_admin(tg_id):
    if tg_id != ADMIN_ID:
        abort(403)

@app.route("/orders")
def orders():
    tg_id = int(request.args.get("tg_id"))
    check_admin(tg_id)

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/accept", methods=["POST"])
def accept():
    data = request.json
    check_admin(data["tg_id"])

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM orders WHERE id=?", (data["id"],))
    uid = cur.fetchone()[0]
    cur.execute("UPDATE orders SET status='ACCEPTED' WHERE id=?", (data["id"],))
    conn.commit()
    conn.close()

    send_msg(uid, "✅ Ta commande est ACCEPTÉE")
    return {"ok": True}

@app.route("/refuse", methods=["POST"])
def refuse():
    data = request.json
    check_admin(data["tg_id"])

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM orders WHERE id=?", (data["id"],))
    uid = cur.fetchone()[0]
    cur.execute("UPDATE orders SET status='REFUSED' WHERE id=?", (data["id"],))
    conn.commit()
    conn.close()

    send_msg(uid, "❌ Ta commande est REFUSÉE")
    return {"ok": True}

app.run(host="0.0.0.0", port=10000)
