from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856  # Log grubunun ID'si
SUDO_ID = 7035704703           # Sudo kullanıcı ID
PENDING_TICKETS = {}           # {user_id: {"id": ticket_id, "type": "hata/sorun/öneri"}}
WAITING_FOR_REPLY = {}         # {sudo_id: user_id}

# ==========================
# /destek komutu
# ==========================
@app.on_message(filters.command("destek"))
async def destek_panel(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🐞 Hata", callback_data="destek_hata"),
            InlineKeyboardButton("💡 Öneri", callback_data="destek_oneri"),
            InlineKeyboardButton("⚙️ Genel Sorun", callback_data="destek_sorun")
        ],
        [InlineKeyboardButton("❌ İptal", callback_data="destek_iptal")]
    ])
    await message.reply_text(
        "**✨ DEEPMusic Destek Paneli**\n\nBir talep türü seçiniz:",
        reply_markup=keyboard
    )

# ==========================
# Talep türü seçimi
# ==========================
@app.on_callback_query(filters.regex("^destek_"))
async def destek_turu_sec(client: Client, cq: CallbackQuery):
    data = cq.data.split("_")[1]
    user_id = cq.from_user.id

    if data == "iptal":
        await cq.message.edit("❌ Talep işlemi iptal edildi.")
        if user_id in PENDING_TICKETS:
            del PENDING_TICKETS[user_id]
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {"id": ticket_id, "type": data}

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❌ İptal", callback_data="destek_iptal")]])

    await cq.message.reply_text(
        f"📝 **Talep ID:** `{ticket_id}`\n"
        f"**Tür:** {data.capitalize()}\n\n"
        "Lütfen mesajınızı veya foto/video/dosya gönderin.\n"
        "İptal etmek için /iptal yazabilir veya aşağıdan iptal edebilirsiniz.",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Kullanıcı talebini gönderiyor (yazı, medya fark etmez)
# ==========================
@app.on_message(filters.create(lambda _, __, msg: msg.from_user.id in PENDING_TICKETS))
async def talep_alindi(client: Client, message: Message):
    user_id = message.from_user.id
    ticket_info = PENDING_TICKETS[user_id]
    ticket_id = ticket_info["id"]
    ticket_type = ticket_info["type"]

    user = message.from_user
    chat_type = "Özel" if message.chat.type == "private" else message.chat.title

    caption = message.caption or message.text or "📎 (Sadece medya)"
    log_text = (
        f"📩 **Yeni Talep!**\n"
        f"**Talep Türü:** {ticket_type.capitalize()}\n"
        f"**Talep ID:** `{ticket_id}`\n"
        f"**Talep Eden:** {user.mention}\n"
        f"**Yazıldığı Yer:** {chat_type}\n"
        f"**Mesaj:** {caption}"
    )

    # Butonlar
    buttons = []
    if message.chat.type in ["supergroup", "group"]:
        link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.id}"
        buttons.append([InlineKeyboardButton("🔗 Mesaja Git", url=link)])

    buttons.append([
        InlineKeyboardButton("🤖 Bot ile Yanıtla", callback_data=f"yanitla_{user_id}"),
        InlineKeyboardButton("👤 Kullanıcıya Git", url=f"tg://user?id={user_id}")
    ])
    buttons.append([InlineKeyboardButton("❌ Talep İptal", callback_data=f"iptal_{ticket_id}")])
    markup = InlineKeyboardMarkup(buttons)

    # Log ve Sudo’ya gönder
    if message.media:
        await message.copy(LOG_GROUP_ID, caption=log_text, reply_markup=markup)
        await message.copy(SUDO_ID, caption=log_text, reply_markup=markup)
    else:
        await client.send_message(LOG_GROUP_ID, log_text, reply_markup=markup)
        await client.send_message(SUDO_ID, log_text, reply_markup=markup)

    # Kullanıcıya yanıt
    await message.reply_text(
        f"✅ Talebiniz alınmıştır.\n**Talep ID:** `{ticket_id}`\nEn kısa sürede dönüş yapılacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )

    del PENDING_TICKETS[user_id]

# ==========================
# Sudo “Bot ile Yanıtla” butonuna basıyor
# ==========================
@app.on_callback_query(filters.regex("^yanitla_"))
async def sudo_yanit_modu(client: Client, cq: CallbackQuery):
    if cq.from_user.id != SUDO_ID:
        await cq.answer("❗ Bu işlem yalnızca yetkili tarafından yapılabilir.", show_alert=True)
        return

    user_id = int(cq.data.split("_")[1])
    WAITING_FOR_REPLY[cq.from_user.id] = user_id

    await cq.message.reply_text(
        f"💬 Lütfen kullanıcıya göndermek istediğiniz yanıtı yazın veya medya gönderin.\n"
        f"ID: `{user_id}`",
        parse_mode=ParseMode.MARKDOWN
    )

# ==========================
# Sudo yanıt gönderiyor (her şey destekli)
# ==========================
@app.on_message(filters.user(SUDO_ID))
async def sudo_mesaj_gonder(client: Client, message: Message):
    sudo_id = message.from_user.id
    if sudo_id not in WAITING_FOR_REPLY:
        return

    user_id = WAITING_FOR_REPLY[sudo_id]
    del WAITING_FOR_REPLY[sudo_id]

    try:
        if message.media:
            await message.copy(user_id, caption=message.caption or "💬 **Destek Yanıtı:**")
        elif message.text:
            await client.send_message(user_id, f"💬 **Destek Yanıtı:**\n{message.text}")
        else:
            await client.send_message(user_id, "💬 Destek ekibinden bir yanıt geldi.")

        await message.reply_text("✅ Yanıt kullanıcıya başarıyla gönderildi.")
    except Exception as e:
        await message.reply_text(f"⚠️ Kullanıcıya mesaj gönderilemedi.\n`{e}`")

# ==========================
# Talep iptali
# ==========================
@app.on_callback_query(filters.regex("^iptal_"))
async def talep_iptal(client: Client, cq: CallbackQuery):
    await cq.message.edit_text("❌ Talep iptal edildi.")
