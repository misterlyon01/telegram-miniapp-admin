
print("DEBUG: bot.py chargé")
from telegram import WebAppInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.request import HTTPXRequest
from datetime import datetime, timedelta
import sqlite3

# ================= CONFIG =================
TOKEN = "7975345597:AAH_CJ5aT8W_bZvfk5tCwgheDerncht5jvE"
ADMIN_ID = 5869177453

PRODUCTS = {
    "mousseux": "🍮 Mousseux",
    "filtraxxx": "🍫 Filtraxxx",
    "beuguiii": "🥦 Beuguiii"
}

PRICE_BUTTONS = [10, 20, 30, 40, 50]
START_HOUR = 10
END_HOUR = 22

orders = {}
reserved_slots = set()

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            products TEXT,
            total INTEGER,
            mode TEXT,
            address TEXT,
            phone TEXT,
            slot TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_order(uid):
    o = orders[uid]
    products_txt = " | ".join(
        [f"{PRODUCTS[i['product']]} ({i['price']}€)" for i in o["cart"]]
    )
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders
        (user_id, products, total, mode, address, phone, slot, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uid,
        products_txt,
        cart_total(uid),
        o["mode"],
        o.get("address"),
        o["phone"],
        o["slot"],
        "PENDING",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# ================= UTILS =================
def generate_slots():
    slots = []
    t = datetime.strptime(f"{START_HOUR}:00", "%H:%M")
    end = datetime.strptime(f"{END_HOUR}:00", "%H:%M")
    while t <= end:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=30)
    return slots

SLOTS = generate_slots()
request = HTTPXRequest(connect_timeout=15, read_timeout=15)

def init_order(uid):
    orders[uid] = {
        "cart": [],
        "current_product": None,
        "step": "products",
        "mode": None,
        "address": None,
        "phone": None,
        "slot": None
    }

def cart_total(uid):
    return sum(i["price"] for i in orders[uid]["cart"])

# ================= UI =================
async def show_products(q):
    kb = [[InlineKeyboardButton(v, callback_data=f"P_{k}")]
          for k, v in PRODUCTS.items()]
    await q.edit_message_text(
        "🛒 Choisis un produit :",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_prices(q):
    kb = []
    for p in PRICE_BUTTONS:
        kb.append([InlineKeyboardButton(f"{p} €", callback_data=f"PRICE_{p}")])
    kb.append([InlineKeyboardButton("➕ Autre montant", callback_data="PRICE_OTHER")])
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="BACK_PRODUCTS")])

    await q.edit_message_text(
        "💰 Choisis le prix :",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_cart(q, uid):
    text = "🧾 PANIER\n\n"
    for i in orders[uid]["cart"]:
        text += f"- {PRODUCTS[i['product']]} : {i['price']} €\n"
    text += f"\nTotal : {cart_total(uid)} €"

    kb = [
        [InlineKeyboardButton("➕ Ajouter un produit", callback_data="ADD_MORE")],
        [InlineKeyboardButton("➡️ Continuer", callback_data="CONTINUE")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="BACK_PRICES")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def show_mode(q, uid):
    kb = []
    if cart_total(uid) >= 30:
        kb.append([InlineKeyboardButton("🚚 Livraison", callback_data="MODE_DELIVERY")])
    kb.append([InlineKeyboardButton("📍 Sur place", callback_data="MODE_PLACE")])
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="BACK_CART")])

    await q.edit_message_text(
        "🚚 Mode de récupération :",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_slots(q):
    kb = [[InlineKeyboardButton(s, callback_data=f"S_{s}")]
          for s in SLOTS if s not in reserved_slots]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="BACK_MODE")])

    await q.edit_message_text(
        "⏰ Choisis un horaire :",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def show_recap(q, uid):
    text = "🧾 RÉCAPITULATIF\n\n"
    for i in orders[uid]["cart"]:
        text += f"- {PRODUCTS[i['product']]} : {i['price']} €\n"

    text += (
        f"\nTotal : {cart_total(uid)} €\n"
        f"Mode : {orders[uid]['mode']}\n"
        f"Horaire : {orders[uid]['slot']}\n"
        f"Téléphone : {orders[uid]['phone']}\n"
        f"Adresse : {orders[uid].get('address','📍 Envoyée après validation')}"
    )

    kb = [
        [InlineKeyboardButton("✅ Confirmer la commande", callback_data="SEND")],
        [InlineKeyboardButton("⬅️ Modifier", callback_data="BACK_SLOT")]
    ]
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    init_order(uid)
    await update.message.reply_text("Bienvenue 👋")
    await show_products(
        type("Q", (), {"edit_message_text": update.message.reply_text})
    )

# ================= CALLBACKS =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    d = q.data

    if d.startswith("P_"):
        orders[uid]["current_product"] = d.replace("P_", "")
        orders[uid]["step"] = "prices"
        await show_prices(q)

    elif d.startswith("PRICE_"):
        if d == "PRICE_OTHER":
            orders[uid]["step"] = "custom_price"
            await q.edit_message_text("✏️ Entre le montant souhaité :")
        else:
            orders[uid]["cart"].append({
                "product": orders[uid]["current_product"],
                "price": int(d.replace("PRICE_", ""))
            })
            await show_cart(q, uid)

    elif d == "ADD_MORE":
        await show_products(q)

    elif d == "CONTINUE":
        orders[uid]["step"] = "mode"
        await show_mode(q, uid)

    elif d.startswith("MODE_"):
        orders[uid]["mode"] = d
        if d == "MODE_DELIVERY":
            orders[uid]["step"] = "address"
            await q.edit_message_text("📍 Entre ton adresse :")
        else:
            orders[uid]["step"] = "phone"
            await q.edit_message_text("📞 Entre ton numéro de téléphone :")

    elif d.startswith("S_"):
        orders[uid]["slot"] = d.replace("S_", "")
        orders[uid]["step"] = "recap"
        await show_recap(q, uid)

    elif d == "SEND":
        save_order(uid)
        reserved_slots.add(orders[uid]["slot"])

        recap = "📥 NOUVELLE COMMANDE\n\n"
        for i in orders[uid]["cart"]:
            recap += f"- {PRODUCTS[i['product']]} : {i['price']} €\n"
        recap += (
            f"\nTotal : {cart_total(uid)} €\n"
            f"Mode : {orders[uid]['mode']}\n"
            f"Horaire : {orders[uid]['slot']}\n"
            f"Téléphone : {orders[uid]['phone']}\n"
            f"Adresse : {orders[uid].get('address','À envoyer')}\n"
            f"Client ID : {uid}"
        )

        await context.bot.send_message(ADMIN_ID, recap)
        await q.edit_message_text("⏳ Commande envoyée. En attente de validation.")

    elif d.startswith("BACK_"):
        if d == "BACK_PRODUCTS":
            await show_products(q)
        elif d == "BACK_PRICES":
            await show_prices(q)
        elif d == "BACK_CART":
            await show_cart(q, uid)
        elif d == "BACK_MODE":
            await show_mode(q, uid)
        elif d == "BACK_SLOT":
            await show_slots(q)

# ================= TEXTE UNIQUE =================
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    if orders[uid]["step"] == "custom_price":
        try:
            price = int(text)
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Montant invalide.")
            return

        orders[uid]["cart"].append({
            "product": orders[uid]["current_product"],
            "price": price
        })

        await show_cart(
            type("Q", (), {"edit_message_text": update.message.reply_text}),
            uid
        )

    elif orders[uid]["step"] == "address":
        orders[uid]["address"] = text
        orders[uid]["step"] = "phone"
        await update.message.reply_text("📞 Entre ton numéro de téléphone :")

    elif orders[uid]["step"] == "phone":
        orders[uid]["phone"] = text
        orders[uid]["step"] = "slot"
        await show_slots(
            type("Q", (), {"edit_message_text": update.message.reply_text})
        )
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [[InlineKeyboardButton(
        "🖥️ Panel Admin",
        web_app=WebAppInfo(
            url="https://example.com"  # remplacé après hébergement
        )
    )]]

    await update.message.reply_text(
        "Accès au panel admin :",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= APP =================
init_db()
app = ApplicationBuilder().token(TOKEN).request(request).build()


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("panel", panel))
app.add_handler(CallbackQueryHandler(callbacks))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

print("🤖 BOT FINAL OPÉRATIONNEL")
app.run_polling()
