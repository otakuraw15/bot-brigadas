import os
import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 1. Inicializar la base de datos SQLite sencilla
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


# 2. Recibir la ubicación que comparte el brigadista
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    context.user_data["lat"] = loc.latitude
    context.user_data["lon"] = loc.longitude
    await update.message.reply_text(
        "📍 ¡Ubicación recibida con éxito!\nAhora, envíame **solo el número total de volantes** entregados en este punto (ej. 350)."
    )


# 3. Recibir el número de volantes y guardar todo en la base de datos
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

        # Guardar en SQLite
        conn = sqlite3.connect("brigadas.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO registros (usuario, latitud, longitud, volantes) VALUES (?, ?, ?, ?)",
            (usuario, lat, lon, volantes),
        )
        conn.commit()
        conn.close()

        # Limpiar datos temporales del usuario
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ ¡Registro guardado correctamente!\nSe registraron {volantes} volantes."
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, escribe únicamente un número válido (ej. 400)."
        )


# 4. Comando para descargar la base de datos directamente al chat
async def descargar_bd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("brigadas.db"):
        await update.message.reply_document(
            document=open("brigadas.db", "rb"),
            caption="📂 Aquí tienes tu base de datos actualizada.",
        )
    else:
        await update.message.reply_text(
            "⚠️ Aún no hay registros guardados en la base de datos."
        )


if __name__ == "__main__":
    # PEGA TU TOKEN DE BOTFATHER AQUÍ ENTRE LAS COMILLAS:
    TOKEN = "8898604362:AAGc2k3_E6j-gKUpl3nsaXV5JC__62B8xew"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("descargar", descargar_bd))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

    print("🤖 Bot de brigadas iniciado y escuchando...")
    app.run_polling()