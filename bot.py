import os
import re
import asyncio
import socket
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# --- Render Port Binding Fix ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    while True:
        try:
            client_conn, _ = server_socket.accept()
            response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
            client_conn.sendall(response)
            client_conn.close()
        except Exception:
            pass

threading.Thread(target=run_dummy_server, daemon=True).start()
# -------------------------------

BOT_TOKEN = "8816784739:AAH56XUXvtQ6j869KOAoMZNYXwiUfpa6grk"
DOWNLOAD_DIR = "bot_downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **नमस्ते!**\n\n"
        "मुझे किसी भी **YouTube वीडियो का लिंक** भेजें, "
        "मैं उसे 320kbps MP3 ऑडियो में बदलकर आपको भेज दूँगा।"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # लिंक वैलिडेशन
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("❌ कृपया केवल वैध YouTube वीडियो का लिंक भेजें।")
        return

    status_msg = await update.message.reply_text("⏳ ऑडियो डाउनलोड व कन्वर्ट हो रहा है, कृपया प्रतीक्षा करें...")
    
    out_template = os.path.join(DOWNLOAD_DIR, f"%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'cookiefile': 'cookies.txt',
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        loop = asyncio.get_event_loop()
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Audio')
                uploader = info.get('uploader', 'Unknown Artist')
                duration = info.get('duration', 0)
                file_id = info.get('id')
                mp3_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.mp3")
                return mp3_path, title, uploader, duration

        mp3_path, title, uploader, duration = await loop.run_in_executor(None, extract)
        
        await status_msg.edit_text("📤 ऑडियो फाइल टेलीग्राम पर भेजी जा रही है...")

        with open(mp3_path, 'rb') as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=title,
                performer=uploader,
                duration=duration,
                caption=f"🎵 **{title}**\n👤 {uploader}\n\n⚡ Converted by Anil Saran Bot",
                parse_mode="Markdown"
            )

        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ एरर आया: {str(e)}")

if __name__ == '__main__':
    print("🤖 Telegram YouTube MP3 Bot Started...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_youtube_link))
    app.run_polling()
