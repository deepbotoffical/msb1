from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

# ==========================
# AYARLAR
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubunun ID'si
SUDO_ID = 7035704703           # Sudo kullanıcı ID
PENDING_TICKETS = {}           # {user_id: ticket_id}
REPLY_SESSIONS = {}            # {sudo_id: user_id}

# ==========================
# DESTEK KOMUTU
# ==========================
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
    text = (
        "✨ **DEEPMusic Destek Paneli**\n\n"
        "Herhangi bir sorununuz veya öneriniz mi var?\n"
        "Aşağıdan talep türünü seçiniz.\n\n"
        "🎶 Keyifli dinlemeler."
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐞 Hata / Sorun", callback_data="ticket_hata"),
            InlineKeyboardButton("💡 Öneri", callback_data="ticket_oneri")
        ],
        [
            InlineKeyboardButton("📋 Genel Destek", callback_data="ticket_genel")
        ],
        [
            InlineKeyboardButton("❌ İptal", callback_data="cancel_ticket")
        ]
    ])
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==========================
# TALEP OLUŞTURMA
# ==========================
@app.on_callback_query(filters.regex("^ticket_"))
async def open_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[1].capitalize()

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten açık bir talebiniz var!", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {"id": ticket_id, "type": ticket_type}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal Et", callback_data="cancel_ticket")]])
    await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\n"
        f"📂 Tür: **{ticket_type}**\n\n"
        f"Lütfen mesajınızı yazın veya medya (foto/video/dosya) gönderin.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# ==========================
# TALEP ALMA
# ==========================
@app.on_message(
    (filters.text | filters.photo | filters.video | filters.document | filters.audio) &
    filters.private &
    filters.create(lambda _, __, msg: msg.from_user.id in PENDING_TICKETS)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    data = PENDING_TICKETS[user_id]
    ticket_id = data["id"]
    ticket_type = data["type"]
    user_mention = message.from_user.mention
    chat_type = "Özel Mesaj"

    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"📂 Tür: `{ticket_type}`\n"
        f"🪪 Talep ID: `{ticket_id}`\n"
        f"👤 Talep Eden: {user_mention}\n"
        f"💬 Yazıldığı Yer: {chat_type}\n\n"
        f"📨 Mesaj:\n"
    )

    # Butonlar
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Bot ile Yanıtla", callback_data=f"reply_to:{user_id}")],
        [InlineKeyboardButton("❌ Talebi İptal Et", callback_data="cancel_ticket")]
    ])

    # Mesaj / medya gönderimi
    if message.text:
        await client.send_message(LOG_GROUP_ID, log_text + message.text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        await client.send_message(SUDO_ID, log_text + message.text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        caption = log_text
        if message.caption:
            caption += message.caption
        await message.copy(LOG_GROUP_ID, caption=caption, reply_markup=keyboard)
        await message.copy(SUDO_ID, caption=caption, reply_markup=keyboard)

    # Kullanıcıya bilgi
    await message.reply_text(
        f"✅ Talebiniz alındı.\n📨 Talep ID: `{ticket_id}`\n"
        f"En kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    del PENDING_TICKETS[user_id]

# ==========================
# SUDO BOT ÜZERİNDEN YANIT
# ==========================
@app.on_callback_query(filters.regex("^reply_to:(\\d+)$"))
async def start_sudo_reply(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split(":")[1])
    REPLY_SESSIONS[callback_query.from_user.id] = user_id
    await callback_query.message.reply_text(
        f"✉️ Lütfen yanıtınızı yazın veya medya gönderin.\n"
        f"Bu mesaj kullanıcıya bot aracılığıyla iletilecektir.\n\n"
        f"İptal etmek için /iptal yazabilirsiniz."
    )

@app.on_message(
    filters.private &
    (filters.text | filters.photo | filters.video | filters.document | filters.audio) &
    filters.user(SUDO_ID)
)
async def sudo_reply_message(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in REPLY_SESSIONS:
        return

    user_id = REPLY_SESSIONS[sudo_id]
    try:
        if message.text:
            await client.send_message(
                user_id,
                f"📬 **Destek Yanıtı:**\n\n{message.text}"
            )
        else:
            caption = message.caption or "📬 **Destek Yanıtı**"
            await message.copy(user_id, caption=caption)

        await message.reply_text("✅ Yanıt başarıyla kullanıcıya gönderildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi.\nSebep: `{e}`")

    del REPLY_SESSIONS[sudo_id]

# ==========================
# TALEP İPTALİ
# ==========================
@app.on_callback_query(filters.regex("cancel_ticket"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.message.edit_text("❌ Talep iptal edildi.")
    elif user_id in REPLY_SESSIONS:
        del REPLY_SESSIONS[user_id]
        await callback_query.message.edit_text("🛑 Yanıt oturumu iptal edildi.")
    else:
        await callback_query.answer("Şu anda aktif bir işlem yok.", show_alert=True)
