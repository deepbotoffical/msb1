from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
import random
import asyncio

app = Client("my_bot")

LOG_GROUP_ID = -1002663919856
SUDO_IDS = [7035704703]

PENDING_TICKETS = {}          # {user_id: {"ticket_id":..., "type":..., "chat_type":..., "message":...}}
PENDING_ADMIN_REPLY = {}      # {sudo_id: {"target_user":..., "ticket_id":...}}
CLOSED_TICKETS = set()
REMINDER_DELAY_MINUTES = 30   # Örnek varsayılan

# -------------------------
# Destek Paneli
# -------------------------
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📝 Öneri", callback_data="ticket_type_suggestion"),
                InlineKeyboardButton("❌ Hata", callback_data="ticket_type_bug"),
                InlineKeyboardButton("💡 Genel Sorun", callback_data="ticket_type_issue"),
            ],
            [
                InlineKeyboardButton("❌ İptal", callback_data="cancel_init")
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
# Talep Türü Seçildi
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
    msg = await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\nLütfen talebinizi yazın veya foto/video/dosya gönderin.\n"
        "İptal etmek için /iptal yazabilirsiniz.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data=f"cancel_{ticket_id}")]]),
        parse_mode=ParseMode.MARKDOWN
    )

    PENDING_TICKETS[user_id] = {"ticket_id": ticket_id, "type": ticket_type, "chat_type": chat_type, "message": msg}

# -------------------------
# Talep Mesajını Alma
# -------------------------
@app.on_message(
    (filters.private | filters.group) &
    ~filters.user(SUDO_IDS) &
    (filters.text | filters.photo | filters.document | filters.video | filters.audio)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    info = PENDING_TICKETS[user_id]
    ticket_id = info["ticket_id"]
    ticket_type = info["type"]
    chat_type = info["chat_type"]

    # Kullanıcının mesajı
    if message.text:
        user_msg = message.text
    else:
        user_msg = f"Medya gönderildi: {message.media.value if message.media else 'Dosya'}"

    # Log mesajı
    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep türü: `{ticket_type}`\n"
        f"Talep eden: {message.from_user.mention}\n"
        f"Yazıldığı yer: {chat_type}\n"
        f"Mesaj: {user_msg}"
    )

    # Butonlar
    buttons = []

    # Grup talepleri
    if message.chat.type != "private":
        msg_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        buttons.append([InlineKeyboardButton("📄 Mesaja git", url=msg_link)])
    profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
    if profile_url:
        buttons.append([InlineKeyboardButton("👤 Kullanıcıya git", url=profile_url)])
    buttons.append([InlineKeyboardButton("💬 Bot üzerinden yanıtla", callback_data=f"reply_{ticket_id}")])
    buttons.append([InlineKeyboardButton("❌ Talep iptal", callback_data=f"cancel_{ticket_id}")])

    keyboard = InlineKeyboardMarkup(buttons)

    # Log ve sudo
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    for sudo_id in SUDO_IDS:
        await client.send_message(sudo_id, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`", parse_mode=ParseMode.MARKDOWN)

    # Talep tamamlandı
    del PENDING_TICKETS[user_id]

# -------------------------
# Talep iptal
# -------------------------
@app.on_callback_query(filters.regex(r"cancel_\d+|cancel_init"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data == "cancel_init":
        await callback_query.message.edit_text("❌ Destek talebi iptal edildi.")
        return

    ticket_id = int(data.split("_")[1])
    # Kullanıcıyı bul
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

# -------------------------
# Sudo Bot Yanıt
# -------------------------
@app.on_callback_query(filters.regex(r"reply_(\d+)"))
async def admin_reply_start(client: Client, callback_query: CallbackQuery):
    sudo_id = callback_query.from_user.id
    ticket_id = int(callback_query.data.split("_")[1])

    # Kullanıcıyı bul
    user_id = None
    for uid, info in PENDING_TICKETS.items():
        if info["ticket_id"] == ticket_id:
            user_id = uid
            break

    PENDING_ADMIN_REPLY[sudo_id] = {"target_user": user_id, "ticket_id": ticket_id}
    await callback_query.answer("✍️ Yanıtınızı yazın, kullanıcıya iletilecek.", show_alert=True)
    await client.send_message(sudo_id, f"💬 Talep `{ticket_id}` için yanıt yazın. İptal için /iptal.")

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

    if target_user:
        try:
            await client.send_message(target_user, f"📬 **Destek Ekibinden Cevap (Talep ID: `{ticket_id}`):**\n\n{message.text}")
            await message.reply_text("✅ Mesaj kullanıcıya iletildi.")
        except Exception as e:
            await message.reply_text(f"❌ Kullanıcıya iletilemedi: {e}")
    else:
        await message.reply_text("❌ Kullanıcı bulunamadı veya grup talebi iletilemiyor.")

# -------------------------
# Talep kapatma
# -------------------------
@app.on_callback_query(filters.regex(r"close_ticket:(\d+)"))
async def close_ticket(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split(":")[1])
    CLOSED_TICKETS.add(ticket_id)
    await callback_query.edit_message_text(f"✅ Talep Kapatıldı\nTalep ID: `{ticket_id}`")
    await callback_query.answer("Talep başarıyla kapatıldı ✅", show_alert=True)

# -------------------------
# Botu çalıştır
# -------------------------
app.run()
