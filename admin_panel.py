from flask import Flask, redirect, url_for
import sqlite3
import requests

# ================= CONFIG =================
BOT_TOKEN = "7975345597:AAH_CJ5aT8W_bZvfk5tCwgheDerncht5jvE"   # MÊME TOKEN QUE bot.py
app = Flask(__name__)

# ================= TELEGRAM =================
def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, data=data)

# ================= DATABASE =================
def get_orders():
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return data

# ================= ROUTES =================
@app.route("/")
def index():
    orders = get_orders()

    html = """
    <h2>📊 PANEL ADMIN</h2>
    <table border="1" cellpadding="6">
        <tr>
            <th>ID</th>
            <th>Client</th>
            <th>Produits</th>
            <th>Total</th>
            <th>Mode</th>
            <th>Horaire</th>
            <th>Statut</th>
            <th>Actions</th>
        </tr>
    """

    for o in orders:
        html += f"""
        <tr>
            <td>{o[0]}</td>
            <td><a href="/client/{o[1]}">{o[1]}</a></td>
            <td>{o[2]}</td>
            <td>{o[3]} €</td>
            <td>{o[4]}</td>
            <td>{o[7]}</td>
            <td>{o[8]}</td>
            <td>
                <a href="/accept/{o[0]}">✅</a>
                <a href="/refuse/{o[0]}">❌</a>
            </td>
        </tr>
        """

    html += "</table>"
    return html

@app.route("/client/<int:uid>")
def client(uid):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, products, total, status, created_at
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
    """, (uid,))
    data = cur.fetchall()
    conn.close()

    html = "<h3>📜 Historique client</h3><ul>"
    for o in data:
        html += f"<li>ID {o[0]} | {o[1]} | {o[2]} € | {o[3]} | {o[4]}</li>"
    html += "</ul><a href='/'>⬅️ Retour</a>"
    return html

@app.route("/accept/<int:oid>")
def accept(oid):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    cur.execute("SELECT user_id, address, slot FROM orders WHERE id=?", (oid,))
    uid, address, slot = cur.fetchone()

    cur.execute("UPDATE orders SET status='ACCEPTED' WHERE id=?", (oid,))
    conn.commit()
    conn.close()

    if address:
        send_telegram_message(
            uid,
            f"✅ Ta commande est ACCEPTÉE 🎉\n\n📍 Adresse : {address}\n⏰ Horaire : {slot}"
        )
    else:
        send_telegram_message(
            uid,
            f"✅ Ta commande est ACCEPTÉE 🎉\n⏰ Horaire : {slot}\n📍 L’adresse te sera envoyée."
        )

    return redirect(url_for("index"))

@app.route("/refuse/<int:oid>")
def refuse(oid):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM orders WHERE id=?", (oid,))
    uid = cur.fetchone()[0]

    cur.execute("UPDATE orders SET status='REFUSED' WHERE id=?", (oid,))
    conn.commit()
    conn.close()

    send_telegram_message(uid, "❌ Ta commande a été refusée.")
    return redirect(url_for("index"))

# ================= RUN =================
app.run(debug=True)
