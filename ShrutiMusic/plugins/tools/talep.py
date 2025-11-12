from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random, asyncio

LOG_GROUP_ID = -1002663919856
SUDO_IDS = [7035704703]

# Ticket durumları
PENDING_TICKETS = {}         # {user_id: {"ticket_id":..., "type":..., "chat_type":..., "message_id":...}}
PENDING_ADMIN_REPLY = {}     # {sudo_id: {"target_user":..., "ticket_id":...}}
CLOSED_TICKETS = set()
REMINDER_DELAY_MINUTES = 5   # Default

# -------------------------
# Destek paneli
# -------------------------
@app.on_message(filters.command("destek") & filters.private)
async def support_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📝 Öneri", callback_data="ticket_type_suggestion"),
                InlineKeyboardButton("❌ Hata", callback_data="ticket_type_bug"),
                InlineKeyboardButton("💡 Genel Sorun", callback_data="ticket_type_issue"),
                InlineKeyboardButton("❌ İptal", callback_data="ticket_cancel")
            ]
        ]
    )
    await message.reply_text(
        "✨ **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# -------------------------
# Talep türü seçildi
# -------------------------
@app.on_callback_query(filters.regex(r"ticket_type_(suggestion|bug|issue)"))
async def select_ticket_type(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[2]

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    chat_type = "Özel" if callback_query.message.chat.type == "private" else callback_query.message.chat.title

    # Talep yaz mesajına iptal butonu
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ İptal", callback_data=f"cancel_{ticket_id}")]]
    )
    msg = await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\nLütfen talebinizi yazın veya foto/video/dosya gönderin.\nİptal etmek için /iptal yazabilirsiniz.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

    PENDING_TICKETS[user_id] = {
        "ticket_id": ticket_id,
        "type": ticket_type,
        "chat_type": chat_type,
        "message_id": msg.id
    }

# -------------------------
# Talep mesajını alma
# -------------------------
@app.on_message(
    (filters.private | filters.group) &
    ~filters.user(SUDO_IDS) &
    (filters.text | filters.photo | filters.document | filters.audio)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    info = PENDING_TICKETS[user_id]
    ticket_id = info["ticket_id"]
    ticket_type = info["type"]
    chat_type = info["chat_type"]
    user_mention = message.from_user.mention

    media_file = None
    media_caption = ""
    if message.text:
        media_caption = message.text
    if message.photo:
        media_file = message.photo.file_id
        media_caption = media_caption or "[Fotoğraf gönderildi]"
    elif message.audio:
        media_file = message.audio.file_id
        media_caption = media_caption or "[Ses gönderildi]"
    elif message.document:
        media_file = message.document.file_id
        media_caption = media_caption or f"[Dosya gönderildi: {message.document.file_name}]"

    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep türü: `{ticket_type}`\n"
        f"Talep eden: {user_mention}\n"
        f"Yazıldığı yer: {chat_type}\n"
        f"Mesaj: {media_caption}"
    )

    # Butonlar
    buttons = []
    if message.chat.type != "private":
        msg_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        buttons.append([InlineKeyboardButton("📄 Mesaja git", url=msg_link)])
    profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
    if profile_url:
        buttons.append([InlineKeyboardButton("👤 Kullanıcıya git", url=profile_url)])
    buttons.append([InlineKeyboardButton("💬 Bot üzerinden yanıtla", callback_data=f"admin_reply:{user_id}:{ticket_id}")])
    buttons.append([InlineKeyboardButton("❌ Talep iptal", callback_data=f"cancel_{ticket_id}")])
    keyboard = InlineKeyboardMarkup(buttons)

    # Log ve sudo mesajı (medya varsa birlikte gönder)
    if media_file:
        await client.send_photo(LOG_GROUP_ID, media_file, caption=log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        for sudo_id in SUDO_IDS:
            await client.send_photo(sudo_id, media_file, caption=log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        for sudo_id in SUDO_IDS:
            await client.send_message(sudo_id, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.", parse_mode=ParseMode.MARKDOWN)

    # Talep tamamlandı
    del PENDING_TICKETS[user_id]

# -------------------------
# İptal butonu
# -------------------------
@app.on_callback_query(filters.regex(r"cancel_\d+"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split("_")[1])
    user_id = None
    for uid, info in PENDING_TICKETS.items():
        if info["ticket_id"] == ticket_id:
            user_id = uid
            break
    if user_id:
        del PENDING_TICKETS[user_id]
        await callback_query.answer("❌ Talep iptal edildi.", show_alert=True)
        await callback_query.message.edit_reply_markup(None)
    else:
        await callback_query.answer("❌ Bu talep bulunamadı veya zaten iptal edilmiş.", show_alert=True)

# ==========================
# Sudo Bot Üzerinden Yanıt
# ==========================
@app.on_callback_query(filters.regex(r"^admin_reply:(\d+):(\d+)$"))
async def admin_reply_callback(client: Client, callback_query: CallbackQuery):
    sudo_id = callback_query.from_user.id
    user_id = int(callback_query.matches[0].group(1))
    ticket_id = int(callback_query.matches[0].group(2))

    PENDING_ADMIN_REPLY[sudo_id] = {"target_user": user_id, "ticket_id": ticket_id}
    await callback_query.answer("✍️ Mesajınızı yazın, kullanıcıya iletilecek.", show_alert=True)
    await client.send_message(sudo_id, f"💬 Talep `{ticket_id}` için cevap yazın. İptal için /iptal.")

@app.on_message(filters.text & filters.user(SUDO_IDS))
async def handle_sudo_reply(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in PENDING_ADMIN_REPLY:
        return

    info = PENDING_ADMIN_REPLY.pop(sudo_id)
    target_user = info["target_user"]
    ticket_id = info["ticket_id"]

    if message.text.lower() == "/iptal":
        await message.reply_text("❌ Yanıt iptal edildi.")
        return

    try:
        await client.send_message(target_user, f"📬 **Destek Ekibinden Cevap (Talep ID: `{ticket_id}`):**\n\n{message.text}")
        await message.reply_text("✅ Mesaj kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya iletilemedi: {e}")
