from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random, asyncio

# ==========================
# AYARLAR
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubunun ID'si
SUDO_ID = 7035704703           # Sudo kullanıcı ID
PENDING_TICKETS = {}           # {user_id: {"id": ticket_id, "type": type}}
WAITING_FOR_REPLY = {}         # {sudo_id: user_id}


# ==========================
# DESTEK PANELİ
# ==========================
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐞 Hata / Sorun", callback_data="ticket_hata"),
            InlineKeyboardButton("💡 Öneri", callback_data="ticket_oneri")
        ],
        [InlineKeyboardButton("📋 Genel Destek", callback_data="ticket_genel")],
        [InlineKeyboardButton("❌ İptal", callback_data="cancel_ticket")]
    ])

    await message.reply_text(
        "✨ **DEEPMusic Destek Paneli**\n\nBir sorununuz veya öneriniz mi var?\n"
        "Aşağıdan bir talep türü seçin:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


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

    await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\n"
        f"📂 Tür: **{ticket_type}**\n\n"
        f"Lütfen sorunuzu veya önerinizi yazın ya da foto/video/dosya gönderin.\n"
        f"İptal etmek için /iptal yazabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="cancel_ticket")]])
    )


# ==========================
# TALEP MESAJINI ALMA (her türlü medya/text)
# ==========================
@app.on_message(
    (filters.text | filters.photo | filters.video | filters.document | filters.audio) &
    filters.private
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id

    # Kullanıcının aktif bir talebi yoksa geç
    if user_id not in PENDING_TICKETS:
        return

    data = PENDING_TICKETS[user_id]
    ticket_id = data["id"]
    ticket_type = data["type"]
    user_mention = message.from_user.mention
    chat_type = "Özel"

    # Log metni
    caption = (
        f"📩 **Yeni Talep!**\n"
        f"📂 Tür: `{ticket_type}`\n"
        f"🪪 Talep ID: `{ticket_id}`\n"
        f"👤 Talep Eden: {user_mention}\n"
        f"💬 Yazıldığı Yer: {chat_type}\n\n"
        f"📨 Mesaj:\n"
    )

    # Butonlar
    buttons = [
        [InlineKeyboardButton("💬 Bot ile Yanıtla", callback_data=f"reply_user:{user_id}:{ticket_id}")],
        [InlineKeyboardButton("❌ Talebi İptal Et", callback_data=f"cancel_ticket")]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # Log’a gönder (yazı + medya birleştir)
    if message.caption:
        text_content = f"{caption}{message.caption}"
    elif message.text:
        text_content = f"{caption}{message.text}"
    else:
        text_content = caption + "📷 Medya içeriyor"

    # Eğer medya varsa, gönderi olarak log’a yönlendir
    if message.photo:
        await client.send_photo(LOG_GROUP_ID, message.photo.file_id, caption=text_content, reply_markup=keyboard)
    elif message.video:
        await client.send_video(LOG_GROUP_ID, message.video.file_id, caption=text_content, reply_markup=keyboard)
    elif message.document:
        await client.send_document(LOG_GROUP_ID, message.document.file_id, caption=text_content, reply_markup=keyboard)
    elif message.audio:
        await client.send_audio(LOG_GROUP_ID, message.audio.file_id, caption=text_content, reply_markup=keyboard)
    else:
        await client.send_message(LOG_GROUP_ID, text_content, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya bilgi mesajı
    await message.reply_text(
        f"✅ Talebiniz alınmıştır.\n🪪 Talep ID: `{ticket_id}`\nEn kısa sürede dönüş yapılacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    # Talep tamamlandı
    del PENDING_TICKETS[user_id]


# ==========================
# BOT İLE YANIT BUTONU
# ==========================
@app.on_callback_query(filters.regex(r"^reply_user:(\d+):(\d+)$"))
async def reply_user_button(client: Client, callback_query: CallbackQuery):
    sudo_id = callback_query.from_user.id
    user_id = int(callback_query.matches[0].group(1))
    ticket_id = callback_query.matches[0].group(2)

    if sudo_id != SUDO_ID:
        await callback_query.answer("Bu işlemi sadece yetkili kişi yapabilir.", show_alert=True)
        return

    WAITING_FOR_REPLY[sudo_id] = user_id
    await callback_query.answer("✍️ Yanıtınızı yazın, kullanıcıya gönderilecek.", show_alert=True)
    await client.send_message(sudo_id, f"💬 Lütfen mesajınızı yazın. (Talep ID: `{ticket_id}`)", parse_mode=ParseMode.MARKDOWN)


# ==========================
# SUDO MESAJ GÖNDERİNCE KULLANICIYA İLET
# ==========================
@app.on_message(filters.user(SUDO_ID) & filters.text)
async def handle_sudo_reply(client: Client, message: Message):
    sudo_id = message.from_user.id

    if sudo_id not in WAITING_FOR_REPLY:
        return

    user_id = WAITING_FOR_REPLY.pop(sudo_id)
    text = message.text

    try:
        await client.send_message(
            user_id,
            f"📬 **Destek Ekibinden Cevap:**\n\n{text}",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("✅ Yanıt kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya mesaj gönderilemedi.\nHata: {e}")


# ==========================
# TALEP İPTALİ
# ==========================
@app.on_callback_query(filters.regex("cancel_ticket"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.message.reply_text("❌ Talebiniz iptal edildi.")
    await callback_query.answer("Talep iptal edildi.", show_alert=True)
