# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
#
# All rights reserved.
#
# This code is the intellectual property of Nand Yaduwanshi.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: badboy809075@gmail.com


from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import config
import random

# ==========================
# Ayarlar
# ==========================
LOG_GROUP_ID = -1002663919856  # Buraya log grubun ID'si
SUDO_ID = 7035704703  # Sudo kullanıcı ID
ACTIVE_TICKETS = {}  # Talep açan kullanıcılar için geçici kayıt

# ==========================
# DESTEK PANELİ KOMUTU
# ==========================
@app.on_message(filters.command("destek") & ~filters.edited)
async def support_panel(client, message: Message):
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
    ticket_id = random.randint(1000, 9999)  # Basit ID
    ACTIVE_TICKETS[user_id] = ticket_id

    await callback_query.answer(f"📝 Lütfen sorunuzu veya önerinizi yazınız.\nTalep ID: {ticket_id}", show_alert=True)

    # Kullanıcının yazacağı mesajı bekle
    @app.on_message(filters.private & filters.incoming & filters.user(user_id))
    async def receive_ticket(c: Client, msg: Message):
        user_msg = msg.text
        user_mention = msg.from_user.mention
        chat_type = "Özel" if msg.chat.type == "private" else msg.chat.title

        # Log mesajı
        log_text = (
            f"📩 **Yeni Talep!**\n"
            f"Talep ID: `{ticket_id}`\n"
            f"Talep eden: {user_mention}\n"
            f"Mesaj: {user_msg}\n"
            f"Yazıldığı yer: {chat_type}"
        )

        # Yönlendirme butonu
        if msg.chat.type == "private":
            btn_url = f"https://t.me/{msg.from_user.username}" if msg.from_user.username else f"https://t.me/c/{str(msg.chat.id)[4:]}/{msg.message_id}"
        else:
            btn_url = f"https://t.me/c/{str(msg.chat.id)[4:]}/{msg.message_id}"

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Yanıtla", url=btn_url)]]
        )

        # Log grubuna ve sudo kullanıcıya gönder
        await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        await client.send_message(SUDO_ID, log_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

        # Kullanıcıya onay mesajı
        await msg.reply_text(
            f"✅ Talebiniz alınmıştır. Talep ID: `{ticket_id}`\nEn kısa sürede dönüş sağlanacaktır.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Talep tamamlandı → ACTIVE_TICKETS kaydını sil
        del ACTIVE_TICKETS[user_id]

        # Handler'ı kaldır
        app.remove_handler(receive_ticket)
