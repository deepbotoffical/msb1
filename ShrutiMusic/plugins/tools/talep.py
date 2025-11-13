from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
from datetime import datetime

LOG_GROUP_ID = -1002663919856
SUDO_ID = 7035704703

# {user_id: {"ticket_id":..., "type":..., "messages":[str,...], "timestamp":...}}
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
            ],
            [
                InlineKeyboardButton("❌ Talep İptal", callback_data="cancel_ticket")
            ]
        ]
    )
    await message.reply_text(
        "🎧 **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin veya mevcut talebi iptal edin:",
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
        f"Lütfen mesajınızı yazın.\n"
        f"İptal etmek için /iptal yazabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Talep iptal
@app.on_message(filters.command("iptal"))
async def cancel_ticket_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await message.reply_text("❌ Talebiniz iptal edildi.")
        # Sudo'ya bilgi gönder
        await client.send_message(SUDO_ID, f"ℹ️ Kullanıcı {user_id} talebini iptal etti.")
    elif user_id in SUDO_REPLY:
        del SUDO_REPLY[user_id]
        await message.reply_text("❌ Yanıt işlemi iptal edildi.")
    else:
        await message.reply_text("ℹ️ Aktif bir talep veya yanıt işlemi bulunmuyor.")

@app.on_callback_query(filters.regex(r"cancel_ticket"))
async def cancel_ticket_btn(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.message.edit_text("❌ Talep iptal edildi.")
        await callback_query.answer()
        await client.send_message(SUDO_ID, f"ℹ️ Kullanıcı {user_id} talebini iptal etti.")
    else:
        await callback_query.answer("ℹ️ Aktif bir talep bulunmuyor.", show_alert=True)

# ==========================
# Kullanıcının yazısı
@app.on_message(filters.text)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    if message.text.lower() == "/iptal":
        return  # /iptal mesajı burada işleniyor, talep eklenmesin

    PENDING_TICKETS[user_id]["messages"].append(message.text)
    ticket_info = PENDING_TICKETS[user_id]
    ticket_id = ticket_info["ticket_id"]
    ticket_type = ticket_info["type"]
    timestamp = ticket_info["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    user_mention = message.from_user.mention
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    # Log özeti
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📂 Talebi Göster", callback_data=f"show_{user_id}"),
                InlineKeyboardButton("📩 Bot ile Yanıtla", callback_data=f"reply_{user_id}"),
                InlineKeyboardButton("❌ Talep İptal", callback_data=f"cancel_ticket_sudo_{user_id}")
            ]
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

    # Kullanıcıya onay
    await message.reply_text(
        f"✅ Talebiniz alınmıştır.\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Talebi göster
@app.on_callback_query(filters.regex(r"^show_"))
async def show_ticket(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    await callback_query.answer("📄 Talep içeriği getiriliyor...")
    if user_id not in PENDING_TICKETS:
        await callback_query.message.reply_text("⚠️ Talep içeriği alınamadı.")
        return
    messages = "\n".join(PENDING_TICKETS[user_id]["messages"])
    await callback_query.message.reply_text(f"💬 Talep içeriği:\n\n{messages}")

# ==========================
# Bot ile yanıtla
@app.on_callback_query(filters.regex(r"^reply_"))
async def reply_with_bot(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    SUDO_REPLY[callback_query.from_user.id] = user_id
    await callback_query.message.reply_text(
        f"✉️ Kullanıcıya yanıtınızı yazın.\n"
        f"İptal için /iptal yazabilirsiniz."
    )

# ==========================
# Sudo yanıt gönderme
@app.on_message(filters.text & filters.user(SUDO_ID))
async def send_reply_to_user(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in SUDO_REPLY:
        return
    user_id = SUDO_REPLY[sudo_id]

    if message.text.lower() == "/iptal":
        del SUDO_REPLY[sudo_id]
        await message.reply_text("❌ Yanıt işlemi iptal edildi.")
        return

    try:
        await client.send_message(
            user_id,
            f"💬 **DEEPMusic Destek Ekibi tarafından yanıtlandı.**\n\n{message.text}",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("✅ Yanıt başarıyla kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi.\nSebep: {e}")

    del SUDO_REPLY[sudo_id]

# ==========================
# Sudo talep iptal
@app.on_callback_query(filters.regex(r"cancel_ticket_sudo_"))
async def cancel_ticket_sudo(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[-1])
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.message.edit_text("❌ Talep Sudo tarafından iptal edildi.")
        await callback_query.answer()
        await client.send_message(user_id, "❌ Talebiniz iptal edildi.")
    else:
        await callback_query.answer("ℹ️ Aktif bir talep bulunmuyor.", show_alert=True)
