from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

LOG_GROUP_ID = -1002663919856  # Log grubu ID
SUDO_ID = 7035704703
PENDING_TICKETS = {}        # {user_id: ticket_id}
SUDO_REPLY = {}             # {sudo_id: user_id}


# /destek komutu
@app.on_message(filters.command("destek"))
async def destek_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📝 Destek Talebi Oluştur", callback_data="open_ticket")]]
    )
    await message.reply_text(
        "🎧 **DEEPMusic Destek Paneli**\n\n"
        "Sorununuzu veya önerinizi paylaşabilirsiniz.\n"
        "Yardım ekibi en kısa sürede sizinle iletişime geçecektir.",
        reply_markup=keyboard
    )


# Talep başlatma
@app.on_callback_query(filters.regex("open_ticket"))
async def open_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten açık bir talebiniz var.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = ticket_id
    await callback_query.message.reply_text(
        f"📝 Lütfen sorununuzu veya önerinizi yazın ya da medya gönderin.\n"
        f"Talep ID: `{ticket_id}`",
        parse_mode=ParseMode.MARKDOWN
    )


# Kullanıcıdan talep alma (her tür medya dahil)
@app.on_message(filters.create(lambda _, __, msg: msg.from_user and msg.from_user.id in PENDING_TICKETS))
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    ticket_id = PENDING_TICKETS[user_id]
    user_mention = message.from_user.mention
    user_name = message.from_user.first_name

    # Log’a özet bilgi
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📂 Talebi Göster", callback_data=f"show_{user_id}")],
            [InlineKeyboardButton("📩 Bot ile Yanıtla", callback_data=f"reply_{user_id}")]
        ]
    )

    log_text = (
        f"🎟️ **Yeni Destek Talebi**\n\n"
        f"👤 Kullanıcı: {user_mention}\n"
        f"🆔 Talep ID: `{ticket_id}`\n"
        f"🗣️ Ad: {user_name}\n\n"
        f"💬 Talep detayını görmek için aşağıdaki butona tıklayın."
    )

    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard)

    await message.reply_text(
        "✅ Talebiniz alınmıştır.\nEn kısa sürede size dönüş yapılacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    del PENDING_TICKETS[user_id]


# Log grubundan “Talebi Göster” butonu
@app.on_callback_query(filters.regex("^show_"))
async def show_ticket(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    await callback_query.answer("📄 Talep içeriği getiriliyor...")

    try:
        async for msg in client.get_chat_history(user_id, limit=1):
            await msg.copy(callback_query.message.chat.id)
    except Exception:
        await callback_query.message.reply_text("⚠️ Talep içeriği alınamadı. Kullanıcıya ulaşılamıyor olabilir.")


# “Bot ile Yanıtla”
@app.on_callback_query(filters.regex("^reply_"))
async def reply_with_bot(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    SUDO_REPLY[callback_query.from_user.id] = user_id
    await callback_query.message.reply_text(
        f"✉️ {user_id} ID'li kullanıcıya yanıtınızı yazın veya medya gönderin.\n"
        f"İptal için /iptal yazabilirsiniz."
    )


# Sudo yanıt gönderme (metin veya medya)
@app.on_message(filters.create(lambda _, __, msg: msg.from_user and msg.from_user.id in SUDO_REPLY))
async def send_reply_to_user(client: Client, message: Message):
    sudo_id = message.from_user.id
    user_id = SUDO_REPLY[sudo_id]

    try:
        # Yanıtı kopyala
        sent = await message.copy(user_id)
        # Altına destek ibaresi ekle
        await client.send_message(
            user_id,
            "💬 **DEEPMusic Destek Ekibi tarafından yanıtlandı.**",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("✅ Yanıt başarıyla kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi.\nSebep: {e}")

    del SUDO_REPLY[sudo_id]


# Sudo iptal komutu
@app.on_message(filters.command("iptal") & filters.user(SUDO_ID))
async def cancel_reply(client: Client, message: Message):
    if message.from_user.id in SUDO_REPLY:
        del SUDO_REPLY[message.from_user.id]
        await message.reply_text("❌ Yanıtlama işlemi iptal edildi.")
    else:
        await message.reply_text("ℹ️ Aktif bir yanıt işlemi bulunmuyor.")
