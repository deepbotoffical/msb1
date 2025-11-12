from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

LOG_GROUP_ID = -1002663919856
SUDO_IDS = [7035704703]  # Sudo kullanıcı listesi
PENDING_TICKETS = {}      # {user_id: {"ticket_id":..., "chat_type":...}}

# -------------------------
# Destek paneli
# -------------------------
@app.on_message(filters.command("destek"))
async def support_panel(client: Client, message: Message):
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
        "✨ **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# -------------------------
# Talep türü seçildi
# -------------------------
@app.on_callback_query(filters.regex(r"ticket_type_(suggestion|bug|issue)"))
async def select_ticket_type(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[2]

    if user_id in PENDING_TICKETS:
        await callback_query.answer("📌 Zaten bir talebiniz açık.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    chat_type = "Özel" if callback_query.message.chat.type == "private" else callback_query.message.chat.title
    PENDING_TICKETS[user_id] = {"ticket_id": ticket_id, "type": ticket_type, "chat_type": chat_type}

    await callback_query.message.reply_text(
        f"📝 Talep ID: `{ticket_id}`\nLütfen mesajınızı yazınız:",
        parse_mode=ParseMode.MARKDOWN
    )

# -------------------------
# Talep mesajını alma
# -------------------------
@app.on_message(
    filters.private | filters.group &
    ~filters.user(SUDO_IDS) &
    (filters.text | filters.photo | filters.document | filters.audio)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    info = PENDING_TICKETS[user_id]
    ticket_id = info["ticket_id"]
    ticket_type = info["type"]
    chat_type = info["chat_type"]
    user_mention = message.from_user.mention
    user_msg = message.text if message.text else f"Medya gönderildi: {message.media.value}"

    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Talep türü: `{ticket_type}`\n"
        f"Talep eden: {user_mention}\n"
        f"Mesaj: {user_msg}\n"
        f"Yazıldığı yer: {chat_type}"
    )

    # Butonlar
    buttons = []
    if message.chat.type == "private":
        profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
        if profile_url:
            buttons.append([InlineKeyboardButton("👤 Profil", url=profile_url)])
        buttons.append([InlineKeyboardButton("💬 Bot üzerinden yanıtla", callback_data=f"reply_{ticket_id}")])
        buttons.append([InlineKeyboardButton("❌ İptal", callback_data=f"cancel_{ticket_id}")])
    else:
        msg_link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        buttons.append([InlineKeyboardButton("📄 Mesaja git", url=msg_link)])
        profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
        if profile_url:
            buttons.append([InlineKeyboardButton("👤 Kullanıcıya git", url=profile_url)])
        buttons.append([InlineKeyboardButton("💬 Bot üzerinden yanıtla", callback_data=f"reply_{ticket_id}")])
        buttons.append([InlineKeyboardButton("❌ İptal", callback_data=f"cancel_{ticket_id}")])

    keyboard = InlineKeyboardMarkup(buttons)

    # Gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    for sudo_id in SUDO_IDS:
        await client.send_message(sudo_id, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    # Kullanıcıya onay
    await message.reply_text(f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`", parse_mode=ParseMode.MARKDOWN)

    # Talep tamamlandı
    del PENDING_TICKETS[user_id]

# -------------------------
# İptal butonu
# -------------------------
@app.on_callback_query(filters.regex(r"cancel_\d+"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split("_")[1])
    # Kullanıcı ID'yi bul
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

# -------------------------
# Bot üzerinden yanıtla (sadece Sudo)
# -------------------------
@app.on_callback_query(filters.regex(r"reply_\d+"))
async def reply_ticket(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split("_")[1])
    await callback_query.answer(f"💬 Talep ID {ticket_id} için yanıt verebilirsiniz.", show_alert=True)        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nKategori: **{category}**\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    PENDING_TICKETS[user_id]["message_id"] = message.id
    asyncio.create_task(start_ticket_reminder(client, user_id, ticket_id))

# ==========================
# Talep iptal
# ==========================
@app.on_callback_query(filters.regex(r"^cancel_ticket:(\d+)$"))
async def cancel_ticket(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.matches[0].group(1))
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await callback_query.edit_message_text("❌ Talep iptal edildi.")
        try:
            await client.send_message(user_id, "❌ Destek talebiniz iptal edildi.")
        except:
            pass
    else:
        await callback_query.answer("❌ Bu talep zaten kapatılmış.", show_alert=True)

# ==========================
# Sudo Bot Üzerinden Cevap
# ==========================
@app.on_callback_query(filters.regex(r"^admin_reply:(\d+):(\d+)$"))
async def admin_reply_callback(client: Client, callback_query: CallbackQuery):
    sudo_id = callback_query.from_user.id
    user_id = int(callback_query.matches[0].group(1))
    ticket_id = int(callback_query.matches[0].group(2))

    PENDING_ADMIN_REPLY[sudo_id] = {"target_user": user_id, "ticket_id": ticket_id}
    await callback_query.answer("✍️ Mesajınızı yazın, kullanıcıya iletilecek.", show_alert=True)
    await client.send_message(sudo_id, f"💬 Talep `{ticket_id}` için cevap yazın. İptal için /iptal.")

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

    try:
        await client.send_message(target_user, f"📬 **Destek Ekibinden Cevap (Talep ID: `{ticket_id}`):**\n\n{message.text}")
        await message.reply_text("✅ Mesaj kullanıcıya iletildi.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Talebi Kapat", callback_data=f"close_ticket:{ticket_id}")]
        ]))
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya iletilemedi: {e}")

# ==========================
# Talep kapatma
# ==========================
@app.on_callback_query(filters.regex(r"^close_ticket:(\d+)$"))
async def close_ticket(client: Client, callback_query: CallbackQuery):
    ticket_id = int(callback_query.matches[0].group(1))
    CLOSED_TICKETS.add(ticket_id)
    await callback_query.edit_message_text(f"✅ Talep Kapatıldı\nTalep ID: `{ticket_id}`")
    await callback_query.answer("Talep başarıyla kapatıldı ✅", show_alert=True)

# ==========================
# Hatırlatma sistemi
# ==========================
async def start_ticket_reminder(client: Client, user_id: int, ticket_id: int):
    while True:
        await asyncio.sleep(REMINDER_DELAY_MINUTES * 60)
        if user_id in PENDING_TICKETS and PENDING_TICKETS[user_id]["ticket_id"] == ticket_id:
            try:
                await client.send_message(user_id, f"⏰ Talep ID: `{ticket_id}` için henüz cevap gelmedi. En kısa sürede destek ekibimiz dönüş yapacaktır.")
            except:
                pass
            for sudo_id in SUDO_IDS:
                await client.send_message(sudo_id, f"⏰ Talep ID: `{ticket_id}` henüz yanıtlanmadı. Kullanıcı: [{user_id}](tg://user?id={user_id})", parse_mode=ParseMode.MARKDOWN)
        else:
            break

# ==========================
# /sudover komutu
# ==========================
@app.on_message(filters.command("sudover") & filters.user(SUDO_IDS[0]))
async def manage_sudo(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("❌ Kullanım: /sudover <ekle/remove> <user_id>")
        return

    action = args[1].lower()
    try:
        user_id = int(args[2])
    except:
        await message.reply_text("❌ Geçerli bir user_id girin.")
        return

    global SUDO_IDS

    if action in ["ekle", "add"]:
        if user_id not in SUDO_IDS:
            SUDO_IDS.append(user_id)
            await message.reply_text(f"✅ User `{user_id}` Sudo listesine eklendi.")
        else:
            await message.reply_text("❗ Bu kullanıcı zaten Sudo listesinde.")
    elif action in ["remove", "çıkar"]:
        if user_id in SUDO_IDS:
            SUDO_IDS.remove(user_id)
            await message.reply_text(f"✅ User `{user_id}` Sudo listesinden çıkarıldı.")
        else:
            await message.reply_text("❗ Bu kullanıcı Sudo listesinde değil.")
    else:
        await message.reply_text("❌ Geçersiz işlem. Kullanım: /sudover <ekle/remove> <user_id>")

# ==========================
# /hatirlama komutu
# ==========================
@app.on_message(filters.command("hatirlama") & filters.user(SUDO_IDS[0]))
async def set_reminder_time(client: Client, message: Message):
    try:
        minutes = int(message.text.split()[1])
        global REMINDER_DELAY_MINUTES
        REMINDER_DELAY_MINUTES = minutes
        await message.reply_text(f"✅ Hatırlatma süresi {minutes} dakika olarak ayarlandı.")
    except:
        await message.reply_text("❌ Kullanım: /hatirlama <dakika>")
