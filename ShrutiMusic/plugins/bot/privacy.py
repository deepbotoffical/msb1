from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubun ID'si
SUDO_ID = 7035704703  # Sudo kullanıcı ID
ACTIVE_TICKETS = {}  # Aktif talep kayıtları

# ==========================
# DESTEK PANELİ KOMUTU
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
    
    await message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# TALEP BUTONU TIKLANDIĞINDA
# ==========================
@app.on_callback_query(filters.regex("open_ticket"))
async def open_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    # Zaten açık talep varsa uyar
    if user_id in ACTIVE_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık. Lütfen önce onu tamamlayın.", show_alert=True)
        return

    # Talep açılıyor
    ticket_id = random.randint(1000, 9999)
    ACTIVE_TICKETS[user_id] = ticket_id

    # Kullanıcıya mesaj olarak talep yazması gerektiğini bildir
    await callback_query.message.reply_text(
        f"📝 Lütfen sorunuzu veya önerinizi yazınız.\nTalep ID: `{ticket_id}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Kullanıcının mesajını alma
# ==========================
@app.on_message(filters.private & filters.incoming)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id

    if user_id not in ACTIVE_TICKETS:
        return  # Açık talep yoksa çık

    ticket_id = ACTIVE_TICKETS[user_id]
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

    # Yönlendirme butonu
    if message.chat.type == "private":
        btn_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
    else:
        btn_url = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Yanıtla", url=btn_url)]]
    )

    # Log grubuna ve sudo’ya gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay mesajı
    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    # Talep tamamlandı → kayıt sil
    del ACTIVE_TICKETS[user_id]
