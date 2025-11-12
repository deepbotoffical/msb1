from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubunun ID'si
SUDO_ID = 7035704703           # Sudo kullanıcı ID
PENDING_TICKETS = {}           # {user_id: ticket_id}

# ==========================
# Destek paneli komutu
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
# Kullanıcının mesajını alma (hem özel hem grup)
# ==========================
@app.on_message(filters.text)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return  # Talep yoksa çık

    ticket_id = PENDING_TICKETS[user_id]
    user_msg = message.text
    user_mention = message.from_user.mention
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    # Log mesajı
    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep eden: {user_mention}\n"
        f"Mesaj: {user_msg}\n"
        f"Yazıldığı yer: {chat_type}"
    )

    # ==============================
    # Güvenli buton link oluşturma
    # ==============================
    if message.chat.type == "private":
        if message.from_user.username:
            # Kullanıcının kullanıcı adı varsa doğrudan profiline git
            btn_url = f"https://t.me/{message.from_user.username}"
        else:
            # Kullanıcının kullanıcı adı yoksa link gösterme (sadece bilgi butonu)
            btn_url = None
    else:
        # Grup veya kanal mesajı için
        btn_url = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"

    # Buton oluştur
    if btn_url:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Yanıtla", url=btn_url)]])
    else:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Yanıtla", callback_data="no_link")]])

    # Log grubuna ve sudo'ya gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    # Talep tamamlandı → kayıt sil
    del PENDING_TICKETS[user_id]


# ==========================
# Username olmayanlar için uyarı
# ==========================
@app.on_callback_query(filters.regex("no_link"))
async def no_link_warning(client: Client, callback_query: CallbackQuery):
    await callback_query.answer(
        "❗ Bu kullanıcıya doğrudan bağlantı bulunamadı (kullanıcı adı yok).",
        show_alert=True
    )
