from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random, re

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubunun ID'si
SUDO_ID = 7035704703           # Sudo kullanıcı ID
PENDING_TICKETS = {}           # {user_id: ticket_id}
PENDING_ADMIN_REPLY = {}       # {admin_id: {"target_user": user_id, "ticket_id": id}}

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
# Kullanıcının mesajını alma (sadece aktif talebi olanlar)
# ==========================
@app.on_message(filters.text & filters.create(lambda _, __, msg: msg.from_user.id in PENDING_TICKETS))
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
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

    # ==============================
    # Butonlar (duruma göre)
    # ==============================
    buttons = []

    if message.chat.type == "private":
        # Kullanıcı botla özelden konuşuyorsa
        if message.from_user.username:
            profile_btn = InlineKeyboardButton("👤 Kullanıcı Profili", url=f"https://t.me/{message.from_user.username}")
        else:
            profile_btn = InlineKeyboardButton("👤 Kullanıcı Profili", callback_data="no_link")

        reply_btn = InlineKeyboardButton("💬 Bot Üzerinden Yanıtla", callback_data=f"admin_reply:{user_id}:{ticket_id}")
        buttons = [[profile_btn, reply_btn]]

    else:
        # Grup içinden yazılmışsa
        msg_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        link_btn = InlineKeyboardButton("🔗 Mesajı Aç", url=msg_link)
        reply_btn = InlineKeyboardButton("💬 Bot Üzerinden Yanıtla", callback_data=f"admin_reply:{user_id}:{ticket_id}")
        buttons = [[link_btn, reply_btn]]

    keyboard = InlineKeyboardMarkup(buttons)

    # Log grubuna ve sudo'ya gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    del PENDING_TICKETS[user_id]

# ==========================
# Username olmayanlar için uyarı
# ==========================
@app.on_callback_query(filters.regex("no_link"))
async def no_link_warning(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("❗ Kullanıcının profiline ulaşılamıyor (kullanıcı adı yok).", show_alert=True)

# ==========================
# Admin yanıt sistemi
# ==========================
@app.on_callback_query(filters.regex(r"^admin_reply:(\d+):(\d+)$"))
async def admin_reply_callback(client: Client, callback_query: CallbackQuery):
    admin_id = callback_query.from_user.id
    match = re.match(r"^admin_reply:(\d+):(\d+)$", callback_query.data)
    if not match:
        await callback_query.answer("Hata: veriyi okuyamadım.", show_alert=True)
        return

    target_user_id = int(match.group(1))
    ticket_id = match.group(2)
    PENDING_ADMIN_REPLY[admin_id] = {"target_user": target_user_id, "ticket_id": ticket_id}

    await callback_query.answer("✏️ Cevabı yazın — ilk mesaj kullanıcıya iletilecek. /iptal ile iptal edebilirsiniz.", show_alert=True)
    try:
        await client.send_message(admin_id, f"✉️ Talep `{ticket_id}` için cevap yazın. İlk mesaj kullanıcıya iletilecek. İptal için /iptal yazın.")
    except Exception:
        pass

@app.on_message(filters.create(lambda _, __, msg: msg.from_user and msg.from_user.id in PENDING_ADMIN_REPLY))
async def forward_admin_reply(client: Client, message: Message):
    admin_id = message.from_user.id
    info = PENDING_ADMIN_REPLY.pop(admin_id, None)
    if not info:
        return

    target_user = info["target_user"]
    ticket_id = info["ticket_id"]
    text = message.text or ""

    if text.strip().lower() == "/iptal":
        await message.reply_text("❌ Yanıt gönderimi iptal edildi.")
        return

    try:
        send_text = f"🔔 **Destek Ekibinden Cevap (Talep ID: `{ticket_id}`):**\n\n"
        if message.media:
            await client.forward_messages(chat_id=target_user, from_chat_id=message.chat.id, message_ids=message.id)
            await client.send_message(target_user, send_text, parse_mode=ParseMode.MARKDOWN)
        else:
            send_text += text
            await client.send_message(target_user, send_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await message.reply_text(f"❗ Mesaj kullanıcıya iletilemedi: {e}")
        return

    await message.reply_text("✅ Mesaj kullanıcıya başarıyla iletildi.")        await callback_query.answer("❌ Bu talep bulunamadı veya zaten iptal edilmiş.", show_alert=True)

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
