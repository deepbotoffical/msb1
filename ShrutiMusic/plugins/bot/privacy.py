from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

LOG_GROUP_ID = -1002663919856
SUDO_ID = 7035704703

# Aktif talep bekleyen kullanıcılar {user_id: ticket_id}
PENDING_TICKETS = {}

# ==========================
# Destek paneli
# ==========================
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
    text = (
        "✨ **DEEPMusic Destek Paneli**\n\n"
        "Herhangi bir sorununuz veya öneriniz mi var?\n\n"
        "Alttaki butona tıklayınız ve mesajınızı yazınız.\n\n"
        "🎶 Keyifli dinlemeler"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📝 Destek/Talep Gönder", callback_data="open_ticket")]]
    )
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==========================
# Talep butonu
# ==========================
@app.on_callback_query(filters.regex("open_ticket"))
async def open_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık. Lütfen önce onu tamamlayın.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = ticket_id

    await callback_query.message.reply_text(
        f"📝 Lütfen sorunuzu veya önerinizi yazınız.\nTalep ID: `{ticket_id}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Kullanıcının mesajını alma
# ==========================
@app.on_message(filters.text)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    ticket_id = PENDING_TICKETS[user_id]
    user_msg = message.text
    user_mention = message.from_user.mention
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep eden: {user_mention}\n"
        f"Mesaj: {user_msg}\n"
        f"Yazıldığı yer: {chat_type}"
    )

    if message.chat.type == "private":
        btn_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
    else:
        btn_url = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Yanıtla", url=btn_url)]])

    # Log grubuna ve sudo'ya gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    # Talep tamamlandı
    del PENDING_TICKETS[user_id]
