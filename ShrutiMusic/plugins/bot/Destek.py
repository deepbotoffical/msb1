from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random, asyncio

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856
SUDO_IDS = [7035704703]  # Ana Sudo
PENDING_TICKETS = {}       # {user_id: {"ticket_id": id, "category": kategori, "message_id": id}}
PENDING_ADMIN_REPLY = {}   # {sudo_id: {"target_user": id, "ticket_id": id}}
CLOSED_TICKETS = set()     # Kapatılan talepler
REMINDER_DELAY_MINUTES = 24 * 60  # default 24 saat

# ==========================
# /destek komutu ve kategori seçimi
# ==========================
@app.on_message(filters.command("destek") & filters.private)
async def support_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Öneri", callback_data="category:Öneri"),
            InlineKeyboardButton("⚠️ Hata", callback_data="category:Hata"),
            InlineKeyboardButton("❓ Soru", callback_data="category:Soru")
        ]
    ])
    await message.reply_text(
        "✨ **DEEPMusic Destek Paneli**\n\nLütfen talebinizin kategorisini seçin:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Kategori seçimi
# ==========================
@app.on_callback_query(filters.regex(r"^category:(.+)$"))
async def category_selected(client: Client, callback_query: CallbackQuery):
    category = callback_query.matches[0].group(1)
    user_id = callback_query.from_user.id

    if user_id in PENDING_TICKETS:
        await callback_query.answer("❗ Zaten açık bir talebiniz var.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {"ticket_id": ticket_id, "category": category, "message_id": None}

    await callback_query.message.reply_text(
        f"📝 Seçtiğiniz kategori: **{category}**\nLütfen talebinizi yazınız (mesaj, fotoğraf, belge veya ses kabul edilir):",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Kullanıcının mesajını alma (komutlar ve Sudo mesajları hariç)
# ==========================
@app.on_message(
    filters.private &
    ~filters.command &      # Komutları yoksay
    ~filters.user(SUDO_IDS) &  # Sudo mesajlarını yoksay
    (filters.text | filters.photo | filters.document | filters.audio)
)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in PENDING_TICKETS:
        return

    ticket_info = PENDING_TICKETS[user_id]
    ticket_id = ticket_info["ticket_id"]
    category = ticket_info["category"]

    # Mesaj logu
    if message.text:
        content = message.text
    else:
        content = f"Medya gönderildi: {message.media.value}"

    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"Talep ID: `{ticket_id}`\n"
        f"Kullanıcı: {message.from_user.mention} (`{user_id}`)\n"
        f"Kategori: {category}\n"
        f"Mesaj: {content}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔗 Mesaja Git", url=f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}" if message.chat.type != "private" else f"https://t.me/{message.from_user.username}" if message.from_user.username else f"tg://user?id={user_id}"),
            InlineKeyboardButton("📝 Mesajı Yazana Git", url=f"https://t.me/{message.from_user.username}" if message.from_user.username else f"tg://user?id={user_id}")
        ],
        [
            InlineKeyboardButton("🤖 Bot Üzerinden Cevapla", callback_data=f"admin_reply:{user_id}:{ticket_id}"),
            InlineKeyboardButton("❌ Talep İptal", callback_data=f"cancel_ticket:{user_id}")
        ]
    ])

    for sudo in SUDO_IDS + [LOG_GROUP_ID]:
        await client.send_message(sudo, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

    await message.reply_text(
        f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nKategori: **{category}**\nEn kısa sürede dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    PENDING_TICKETS[user_id]["message_id"] = message.id

    # Hatırlatma başlat
    asyncio.create_task(start_ticket_reminder(client, user_id, ticket_id))

# ==========================
# Talep iptal (kullanıcı veya Sudo)
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
# Talep hatırlatma (periyodik)
# ==========================
async def start_ticket_reminder(client: Client, user_id: int, ticket_id: int):
    while True:
        await asyncio.sleep(REMINDER_DELAY_MINUTES * 60)
        if user_id in PENDING_TICKETS and PENDING_TICKETS[user_id]["ticket_id"] == ticket_id:
            try:
                await client.send_message(user_id, f"⏰ Talep ID: `{ticket_id}` için henüz cevap gelmedi. En kısa sürede destek ekibimiz dönüş yapacaktır.", parse_mode=ParseMode.MARKDOWN)
            except:
                pass
            for sudo_id in SUDO_IDS:
                await client.send_message(sudo_id, f"⏰ Talep ID: `{ticket_id}` henüz yanıtlanmadı. Kullanıcı: [{user_id}](tg://user?id={user_id})", parse_mode=ParseMode.MARKDOWN)
        else:
            break  # Talep kapatıldı veya iptal edildi

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
