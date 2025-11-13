from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
import asyncio

LOG_GROUP_ID = -1002663919856
SUDO_IDS = [7035704703]

PENDING_TICKETS = {}          # {user_id: {"ticket_id": ..., "type": ...}}
PENDING_ADMIN_REPLY = {}      # {sudo_id: {"target_user": user_id, "ticket_id": ticket_id}}
CLOSED_TICKETS = set()
REMINDER_DELAY_MINUTES = 5

# ==========================
# Destek paneli
# ==========================
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📝 Öneri", callback_data="ticket_type_suggestion"),
                InlineKeyboardButton("❌ Hata", callback_data="ticket_type_bug"),
                InlineKeyboardButton("💡 Genel Sorun", callback_data="ticket_type_issue"),
                InlineKeyboardButton("❌ İptal", callback_data="cancel_open_ticket")
            ]
        ]
    )
    await message.reply_text(
        "✨ **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Talep türü seçildi
# ==========================
@app.on_callback_query(filters.regex(r"ticket_type_(suggestion|bug|issue)"))
async def select_ticket_type(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[2]

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {"ticket_id": ticket_id, "type": ticket_type}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Talebi İptal Et", callback_data=f"cancel_ticket:{ticket_id}")]])
    await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\nLütfen mesajınızı yazınız veya medya gönderin.\nİptal etmek için /iptal yazabilirsiniz.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Talep iptal (kullanıcı)
# ==========================
@app.on_callback_query(filters.regex(r"cancel_ticket:\d+"))
async def cancel_ticket_user(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split(":")[1])
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
# Talep iptal (destek paneli iptal)
# ==========================
@app.on_callback_query(filters.regex("cancel_open_ticket"))
async def cancel_open_ticket(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.answer("❌ Talep iptal edildi.", show_alert=True)
    else:
        await callback_query.answer("❌ Zaten açık bir talebiniz yok.", show_alert=True)

# ==========================
# Kullanıcı mesajını alma
# ==========================
@app.on_message(
    filters.private | filters.group &
    ~filters.user(SUDO_IDS) &
    (filters.text | filters.photo | filters.video | filters.document | filters.audio)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    info = PENDING_TICKETS[user_id]
    ticket_id = info["ticket_id"]
    ticket_type = info["type"]
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    # Log mesajı
    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep türü: `{ticket_type}`\n"
        f"Talep eden: {message.from_user.mention}\n"
        f"Yazıldığı yer: {chat_type}"
    )

    # Medya veya yazı varsa log ve sudo’ya gönder
    if message.text:
        full_text = f"{log_text}\nMesaj: {message.text}"
        await client.send_message(LOG_GROUP_ID, full_text, parse_mode=ParseMode.MARKDOWN)
        for sudo_id in SUDO_IDS:
            await client.send_message(sudo_id, full_text, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.copy(LOG_GROUP_ID)
        for sudo_id in SUDO_IDS:
            await message.copy(sudo_id)

    # Kullanıcıya onay
    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    del PENDING_TICKETS[user_id]

# ==========================
# Bot üzerinden sudo yanıt
# ==========================
@app.on_callback_query(filters.regex(r"^reply_ticket:(\d+)$"))
async def reply_ticket_callback(client: Client, callback_query: CallbackQuery):
    sudo_id = callback_query.from_user.id
    ticket_id = int(callback_query.data.split(":")[1])
    PENDING_ADMIN_REPLY[sudo_id] = {"ticket_id": ticket_id}
    await callback_query.answer("✍️ Mesajınızı yazın, kullanıcıya iletilecek.", show_alert=True)
    await client.send_message(sudo_id, f"💬 Talep `{ticket_id}` için cevap yazın. /iptal ile iptal edebilirsiniz.")

@app.on_message(filters.user(SUDO_IDS) & filters.text)
async def handle_sudo_reply(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in PENDING_ADMIN_REPLY:
        return

    info = PENDING_ADMIN_REPLY.pop(sudo_id)
    ticket_id = info["ticket_id"]

    if message.text.lower() == "/iptal":
        await message.reply_text("❌ Yanıt iptal edildi.")
        return

    # Kullanıcı ID’yi bul
    user_id = None
    for uid, info_ticket in PENDING_TICKETS.items():
        if info_ticket["ticket_id"] == ticket_id:
            user_id = uid
            break

    if user_id:
        try:
            await client.send_message(user_id, f"📬 **Destek Ekibinden Cevap (Talep ID: `{ticket_id}`):**\n\n{message.text}")
            await message.reply_text("✅ Mesaj kullanıcıya iletildi.")
        except Exception as e:
            await message.reply_text(f"❌ Kullanıcıya iletilemedi: {e}")
    else:
        await message.reply_text("❌ Kullanıcı mesajı bulunamadı veya talep kapatılmış.")
