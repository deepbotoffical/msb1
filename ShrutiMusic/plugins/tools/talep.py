from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
from datetime import datetime

# Lütfen bu değerleri kendi bot ve grup ID'lerinizle değiştirin
# Loglara gönderilen mesajların düzgün çalışması için LOG_GROUP_ID'nin mutlaka doğru olması gerekir.
LOG_GROUP_ID = -1002663919856  # Logların gönderileceği grup ID'si
SUDO_ID = 7035704703          # Yönetici (Sudo) kullanıcının ID'si

# {user_id: {"ticket_id":..., "type":..., "timestamp":...}}
PENDING_TICKETS = {}
SUDO_REPLY = {}  # {sudo_id: user_id}

# ==========================
# /destek komutu: Destek panelini açar
@app.on_message(filters.command("destek"))
async def destek_panel(client: Client, message: Message):
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
        "🎧 **DEEPMusic Destek Paneli**\n\n"
        "Lütfen talep türünüzü seçin:",
        reply_markup=keyboard
    )


# ==========================
# Talep türü seçildi: Kullanıcıyı mesaj göndermeye hazırlar
@app.on_callback_query(filters.regex(r"ticket_type_(suggestion|bug|issue)"))
async def select_ticket_type(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    ticket_type = callback_query.data.split("_")[2]

    # Zaten devam eden bir talep varsa uyarı ver.
    if user_id in PENDING_TICKETS:
        # Önceki mesajı düzeltmek yerine yeni bir mesajla durumu bildir
        await callback_query.message.reply_text("📌 Zaten bir talep gönderme süreciniz açık. Lütfen mesajınızı gönderin veya iptal edin.")
        return

    ticket_id = random.randint(1000, 9999)
    PENDING_TICKETS[user_id] = {
        "ticket_id": ticket_id,
        "type": ticket_type,
        "timestamp": datetime.now()
    }
    
    # İptal butonu içeren klavye
    cancel_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("❌ Talep İptal", callback_data="ticket_cancel")
            ]
        ]
    )
    
    # Kullanıcıya bir sonraki adımı bildir (İptal butonu eklendi)
    await callback_query.edit_message_text(
        f"📝 Talep ID: `{ticket_id}`\n"
        f"Talep Türü: **{ticket_type.capitalize()}**\n\n"
        f"**Lütfen şimdi tek bir mesajla (metin veya medya) talebinizi yazın ve gönderin.**\n"
        f"İptal etmek için `/iptal` yazabilir veya aşağıdaki butonu kullanabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_keyboard
    )
    await callback_query.answer("Talep oluşturma süreci başladı. Lütfen mesajınızı gönderin.")


# ==========================
# Kullanıcıdan Talep İptali (Buton ile)
@app.on_callback_query(filters.regex("ticket_cancel"))
async def cancel_pending_ticket_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id in PENDING_TICKETS:
        # PENDING_TICKETS'ten kullanıcıyı kaldır
        PENDING_TICKETS.pop(user_id, None)
        
        # Mesajı güncelle
        await callback_query.edit_message_text(
            "❌ Talep gönderme işlemi başarıyla iptal edildi.",
            reply_markup=None
        )
        await callback_query.answer("Talep iptal edildi.")
    else:
        # Zaten iptal edilmiş veya hiç açılmamışsa uyarı ver
        await callback_query.answer("Zaten aktif bir talep gönderme süreciniz yoktu.", show_alert=True)


# ==========================
# Kullanıcı mesajı veya medyası: Talebi kesinleştirir ve loglar (Hata 3 Giderildi)
# Sadece özel sohbetteki gelen mesajları dinler
@app.on_message(filters.private & filters.incoming)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Kullanıcının aktif bir talep oluşturma sürecinde olup olmadığını kontrol et
    if user_id not in PENDING_TICKETS:
        return
        
    # Eğer gelen mesaj /iptal komutu ise bu fonksiyonda işlem yapma, diğer handlera bırak
    if message.text and message.text.lower() == "/iptal":
        return

    # Talep mesajını aldık, şimdi kullanıcıyı PENDING_TICKETS'ten çıkarıyoruz.
    # Bu, sonraki mesajların da talep olarak algılanmasını önler.
    ticket_info = PENDING_TICKETS.pop(user_id)
    
    ticket_id = ticket_info["ticket_id"]
    ticket_type = ticket_info["type"]
    timestamp = ticket_info["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    user_mention = message.from_user.mention

    # Log ve Sudo kullanıcısı için butonlar
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📩 Bot ile Yanıtla", callback_data=f"reply_{user_id}")]
        ]
    )

    log_text = (
        f"🎟️ **YENİ DESTEK TALEBİ**\n"
        f"------------------------------\n"
        f"🕓 Tarih: {timestamp}\n"
        f"🆔 Kullanıcı ID: `{user_id}`\n"
        f"👤 Kullanıcı: {user_mention}\n"
        f"💡 Talep Türü: {ticket_type.capitalize()}\n"
        f"Talep ID: `{ticket_id}`\n"
        f"------------------------------\n"
        f"💬 **TALEP İÇERİĞİ HEMEN AŞAĞIDAKİ MESAJDIR.**"
    )
    
    # 1. Log grubuna özeti ve mesajı gönder
    await client.send_message(LOG_GROUP_ID, log_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await message.copy(LOG_GROUP_ID) 

    # 2. Sudo kullanıcısına (özel sohbetine) özeti ve mesajı gönder
    await client.send_message(SUDO_ID, log_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    await message.copy(SUDO_ID) 

    # Kullanıcıya onay mesajı
    await message.reply_text(
        f"✅ Talep ID: `{ticket_id}` ile talebiniz alınmıştır.\n"
        f"En kısa sürede size dönüş sağlanacaktır.",
        parse_mode=ParseMode.MARKDOWN
    )


# ==========================
# Bot ile yanıtla: Sudo yanıt oturumunu başlatır
@app.on_callback_query(filters.regex("^reply_") & filters.user(SUDO_ID))
async def reply_with_bot(client: Client, callback_query: CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    SUDO_REPLY[callback_query.from_user.id] = user_id
    await callback_query.answer("Yanıt oturumu başlatıldı.")
    await client.send_message(
        callback_query.from_user.id,
        f"✉️ Kullanıcıya (`{user_id}`) yanıtınızı yazın veya medya gönderin.\n"
        f"**Birden fazla mesaj gönderebilirsiniz.** Oturumu bitirmek için `/iptal` yazın."
    )


# ==========================
# Sudo yanıt gönderme: Yanıtı kullanıcıya iletir (Hata 2 Giderildi)
# Sadece Sudo kullanıcısının özel sohbetindeki gelen, komut olmayan mesajları dinler
@app.on_message(filters.private & filters.incoming & filters.user(SUDO_ID) & ~filters.command("iptal"))
async def send_reply_to_user(client: Client, message: Message):
    sudo_id = message.from_user.id
    
    if sudo_id not in SUDO_REPLY:
        # Sudo kullanıcısı aktif bir yanıtlama oturumunda değil
        return
    
    user_id = SUDO_REPLY[sudo_id]
    
    try:
        # Yanıt mesajını kullanıcıya kopyala
        await message.copy(user_id)
        
        # Sadece ilk mesajda değil, her yanıtta imza mesajı göndermek gereksiz olabilir.
        # İlk mesajın üzerine yanıt geldiğini belirtelim.
        await message.reply_text("✅ Yanıt başarıyla kullanıcıya iletildi. (Devam edebilirsiniz)")
        
        # Yanıt gönderildiği bilgisini Log Grubuna da ilet
        await client.send_message(
            LOG_GROUP_ID,
            f"✅ **Yanıt İletildi** (ID: `{user_id}`)\n"
            f"Sudo: {message.from_user.mention}\n"
            f"Yanıt Mesajı: (Hemen altta)",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.copy(LOG_GROUP_ID)

    except Exception as e:
        # Hata durumunda oturumu kapat ve Sudo'ya bildir
        del SUDO_REPLY[sudo_id]
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi ve oturum kapatıldı.\nSebep: {e}")
        # Log Grubuna da hatayı ilet
        await client.send_message(
            LOG_GROUP_ID,
            f"❌ **HATA: Yanıt İletilemedi** (ID: `{user_id}`)\n"
            f"Sudo: {message.from_user.mention}\n"
            f"Sebep: {e}",
            parse_mode=ParseMode.MARKDOWN
        )
        

# ==========================
# /iptal komutu: Hem kullanıcı hem de Sudo için tek bir handler
@app.on_message(filters.command("iptal") & filters.private)
async def handle_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Kullanıcı talep gönderme sürecini mi iptal ediyor?
    if user_id in PENDING_TICKETS:
        del PENDING_TICKETS[user_id]
        await message.reply_text("❌ Talep gönderme işlemi iptal edildi.")
        
    # Sudo kullanıcı yanıt oturumunu mu iptal ediyor?
    elif user_id == SUDO_ID and user_id in SUDO_REPLY:
        # Yanıt oturumunu kapat
        user_being_replied = SUDO_REPLY.pop(user_id)
        
        # Log grubuna bilgi ver
        await client.send_message(
            LOG_GROUP_ID,
            f"⛔️ **Yanıt Oturumu Kapatıldı.**\n"
            f"Sudo: {message.from_user.mention}\n"
            f"Kullanıcı ID: `{user_being_replied}`",
            parse_mode=ParseMode.MARKDOWN
        )
        await message.reply_text("❌ Yanıtlama işlemi iptal edildi ve oturum kapatıldı.")
        
    # Aktif bir işlem yoksa
    else:
        await message.reply_text("ℹ️ Aktif bir talep veya yanıt işlemi bulunmuyor.")
