import os
import sqlite3
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Servidor web falso para que Render crea que es una web gratuita y no lo apague
app_web = Flask("")


@app_web.route("/")
def home():
    return "Bot de brigadas activo y funcionando correctamente."


def run_web():
    app_web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


# 1. Inicializar la base de datos SQLite
def init_db():
    conn = sqlite3.connect("brigadas.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            latitud REAL,
            longitud REAL,
            volantes INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


# 2. Recibir ubicación
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    context.user_data["lat"] = loc.latitude
    context.user_data["lon"] = loc.longitude
    await update.message.reply_text(
        "📍 ¡Ubicación recibida!\nAhora envíame **solo el número total de volantes** entregados (ej. 350)."
    )


# 3. Recibir volantes y guardar en BD
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "lat" not in context.user_data:
        await update.message.reply_text(
            "⚠️ Por favor, comparte primero tu ubicación usando el botón de adjuntar de Telegram."
        )
        return

    try:
        volantes = int(update.message.text.strip())
        lat = context.user_data["lat"]
        lon = context.user_data["lon"]
        usuario = (
            update.message.from_user.username
            or update.message.from_user.first_name
        )

        conn = sqlite3.connect("brigadas.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO registros (usuario, latitud, longitud, volantes) VALUES (?, ?, ?, ?)",
            (usuario, lat, lon, volantes),
        )
        conn.commit()
        conn.close()

        context.user_data.clear()
        await update.message.reply_text(
            f"✅ ¡Registro guardado con éxito! Se registraron {volantes} volantes."
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, escribe únicamente un número válido (ej. 400)."
        )


# 4. Comando para descargar la base de datos
async def descargar_bd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("brigadas.db"):
        await update.message.reply_document(
            document=open("brigadas.db", "rb"),
            caption="📂 Aquí tienes tu base de datos actualizada.",
        )
    else:
        await update.message.reply_text(
            "⚠️ Aún no hay registros en la base de datos."
        )


def main():
    TOKEN = "TU_TOKEN_AQUI"  # Reemplaza con tu token de BotFather

    # Arrancamos el servidor web en un hilo secundario para cumplir con Render
    t = Thread(target=run_web)
    t.start()

    # Arrancamos el bot de Telegram
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("descargar", descargar_bd))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    )

    print("🤖 Bot de brigadas iniciado en la nube...")
    app.run_polling()


if __name__ == "__main__":
    main()
