from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
from datetime import datetime

LOG_GROUP_ID = -1002663919856
SUDO_ID = 7035704703

# {user_id: {"ticket_id":..., "type":..., "messages":[Message,...], "timestamp":...}}
PENDING_TICKETS = {}
SUDO_REPLY = {}  # {sudo_id: user_id}

# ==========================
# /destek komutu
@app.on_message(filters.command("destek"))
async def destek_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📝 Öneri", callback_data="ticket_type_suggestion"),
                InlineKeyboardButton("❌ Hata", callback_data="ticket_type_bug"),
                InlineKeyboardButton("💡 Genel Sorun", callback_data="ticket_type_issue")
            ]
        ]
    )
    await message.reply_text(
        "🎧 **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin:",
        reply_markup=keyboard
    )


# ==========================
# Talep türü seçildi
@app.on_callback_query(filters.regex(r"ticket_type_(suggestion|bug|issue)"))
async def select_ticket_type(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[2]

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {
        "ticket_id": ticket_id,
        "type": ticket_type,
        "messages": [],
        "timestamp": datetime.now()
    }

    await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\n"
        f"Talep Türü: **{ticket_type.capitalize()}**\n"
        f"Lütfen mesajınızı yazın veya medya gönderin.\n"
        f"İptal için /iptal yazabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN
    )


# ==========================
# Kullanıcı mesajı veya medyası
@app.on_message(filters.private | filters.group)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    PENDING_TICKETS[user_id]["messages"].append(message)
    ticket_info = PENDING_TICKETS[user_id]
    ticket_id = ticket_info["ticket_id"]
    ticket_type = ticket_info["type"]
    timestamp = ticket_info["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    user_mention = message.from_user.mention
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    # Log özet
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📂 Talebi Göster", callback_data=f"show_{user_id}")],
            [InlineKeyboardButton("📩 Bot ile Yanıtla", callback_data=f"reply_{user_id}")]
        ]
    )

    log_text = (
        f"🎟️ **Yeni Destek Talebi**\n\n"
        f"🕓 Tarih: {timestamp}\n"
        f"🆔 Kullanıcı ID: {user_id}\n"
        f"👤 Kullanıcı: {user_mention}\n"
        f"💡 Talep Türü: {ticket_type.capitalize()}\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Yazıldığı yer: {chat_type}\n\n"
        f"💬 Talep detayını görmek için aşağıdaki butona tıklayın."
    )

    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard)

    await message.reply_text(
        f"✅ Talebiniz alınmıştır.\nEn kısa sürede size dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )


# ==========================
# Talebi göster
@app.on_callback_query(filters.regex("^show_"))
async def show_ticket(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    await callback_query.answer("📄 Talep içeriği getiriliyor...")
    if user_id not in PENDING_TICKETS:
        await callback_query.message.reply_text("⚠️ Talep içeriği alınamadı.")
        return
    try:
        for msg in PENDING_TICKETS[user_id]["messages"]:
            await msg.copy(callback_query.message.chat.id)
    except Exception:
        await callback_query.message.reply_text("⚠️ Talep içeriği iletilemedi.")


# ==========================
# Bot ile yanıtla
@app.on_callback_query(filters.regex("^reply_"))
async def reply_with_bot(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    SUDO_REPLY[callback_query.from_user.id] = user_id
    await callback_query.message.reply_text(
        f"✉️ Kullanıcıya yanıtınızı yazın veya medya gönderin.\n"
        f"İptal için /iptal yazabilirsiniz."
    )


# ==========================
# Sudo yanıt gönderme
@app.on_message(filters.private | filters.group)
async def send_reply_to_user(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in SUDO_REPLY:
        return
    user_id = SUDO_REPLY[sudo_id]
    try:
        await message.copy(user_id)
        await client.send_message(
            user_id,
            "💬 **DEEPMusic Destek Ekibi tarafından yanıtlandı.**",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("✅ Yanıt başarıyla kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi.\nSebep: {e}")
    del SUDO_REPLY[sudo_id]


# ==========================
# Sudo iptal komutu
@app.on_message(filters.command("iptal") & filters.user(SUDO_ID))
async def cancel_reply(client: Client, message: Message):
    if message.from_user.id in SUDO_REPLY:
        del SUDO_REPLY[message.from_user.id]
        await message.reply_text("❌ Yanıtlama işlemi iptal edildi.")
    else:
        await message.reply_text("ℹ️ Aktif bir yanıt işlemi bulunmuyor.")
