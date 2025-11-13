from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
from datetime import datetime

# Lütfen bu değerleri kendi bot ve grup ID'lerinizle değiştirin
LOG_GROUP_ID = -1002663919856  # Logların gönderileceği grup ID'si
SUDO_ID = 7035704703          # Yönetici (Sudo) kullanıcının ID'si

# {user_id: {"ticket_id":..., "type":..., "timestamp":...}}
# Artık sadece durumu (state) tutuyor, mesajları değil.
PENDING_TICKETS = {}
SUDO_REPLY = {}  # {sudo_id: user_id}

# ==========================
# /destek komutu: Destek panelini açar
@app.on_message(filters.command("destek"))
async def destek_panel(client: Client, message: Message):
    # Komutun özel sohbette (private) veya grupta kullanılmasına izin veriyoruz.
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
        await callback_query.answer("📌 Zaten bir talebiniz açık. Lütfen mesajınızı gönderin.", show_alert=True)
        return

    ticket_id = random.randint(1000, 9999)
    # PENDING_TICKETS'e sadece durumu kaydediyoruz.
    PENDING_TICKETS[user_id] = {
        "ticket_id": ticket_id,
        "type": ticket_type,
        "timestamp": datetime.now()
    }
    
    # Kullanıcıya bir sonraki adımı bildir
    await callback_query.edit_message_text(
        f"📝 Talep ID: `{ticket_id}`\n"
        f"Talep Türü: **{ticket_type.capitalize()}**\n\n"
        f"**Lütfen şimdi tek bir mesajla (metin veya medya) talebinizi yazın.**\n"
        f"İptal etmek için `/iptal` yazabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=None # Butonları kaldır
    )
    await callback_query.answer("Talep oluşturma süreci başladı. Lütfen mesajınızı gönderin.")


# ==========================
# Kullanıcı mesajı veya medyası: Talebi kesinleştirir ve loglar (CRITICAL FIX)
# Sadece özel sohbetteki gelen mesajları dinliyoruz.
@app.on_message(filters.private & filters.incoming)
async def receive_ticket(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Kullanıcının aktif bir talep oluşturma sürecinde olup olmadığını kontrol et
    if user_id not in PENDING_TICKETS:
        return

    # Talep mesajını aldık, şimdi kullanıcıyı PENDING_TICKETS'ten çıkarıyoruz (pop)
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
        f"🎟️ **Yeni Destek Talebi**\n\n"
        f"🕓 Tarih: {timestamp}\n"
        f"🆔 Kullanıcı ID: `{user_id}`\n"
        f"👤 Kullanıcı: {user_mention}\n"
        f"💡 Talep Türü: {ticket_type.capitalize()}\n"
        f"Talep ID: `{ticket_id}`\n\n"
        f"💬 **Talep İçeriği Hemen Aşağıdaki Mesajdır.** Yanıtlamak için butonu kullanın."
    )
    
    # 1. Log grubuna özeti ve mesajı gönder
    await client.send_message(LOG_GROUP_ID, log_text, reply_markup=keyboard)
    await message.copy(LOG_GROUP_ID) # Orijinal mesajı kopyala

    # 2. Sudo kullanıcısına (özel sohbetine) özeti ve mesajı gönder
    await client.send_message(SUDO_ID, log_text, reply_markup=keyboard)
    await message.copy(SUDO_ID) # Orijinal mesajı kopyala

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
    await callback_query.answer() # Butona tıklandığını onayla
    await client.send_message(
        callback_query.from_user.id,
        f"✉️ Kullanıcıya ({user_id}) yanıtınızı yazın veya medya gönderin.\n"
        f"İptal için `/iptal` yazabilirsiniz."
    )


# ==========================
# Sudo yanıt gönderme: Yanıtı kullanıcıya iletir
# Sadece Sudo kullanıcısının özel sohbetindeki gelen mesajları dinler
@app.on_message(filters.private & filters.incoming & filters.user(SUDO_ID))
async def send_reply_to_user(client: Client, message: Message):
    sudo_id = message.from_user.id
    
    if sudo_id not in SUDO_REPLY:
        # Sudo kullanıcısı bir yanıt oturumunda değilse normal mesajıdır.
        return

    # Sudo /iptal komutunu burada yakalamıyoruz, dedicated handler'da yakalanacak.
    
    user_id = SUDO_REPLY[sudo_id]
    
    try:
        # Yanıt mesajını kullanıcıya kopyala
        await message.copy(user_id)
        
        # Kullanıcıya imza mesajı gönder
        await client.send_message(
            user_id,
            "💬 **DEEPMusic Destek Ekibi tarafından yanıtlandı.**",
            parse_mode=ParseMode.MARKDOWN
        )
        
        await message.reply_text("✅ Yanıt başarıyla kullanıcıya iletildi.")
    except Exception as e:
        await message.reply_text(f"❌ Kullanıcıya yanıt gönderilemedi.\nSebep: {e}")
        
    # Yanıt gönderildikten sonra oturumu kapat
    del SUDO_REPLY[sudo_id]


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
        del SUDO_REPLY[user_id]
        await message.reply_text("❌ Yanıtlama işlemi iptal edildi.")
        
    # Aktif bir işlem yoksa
    else:
        await message.reply_text("ℹ️ Aktif bir talep veya yanıt işlemi bulunmuyor.")

# NOT: `show_ticket` fonksiyonu, içerik log grubuna ve Sudo'nun özel sohbetine anında 
# kopyalandığı için gereksiz bulunarak kaldırılmıştır.
