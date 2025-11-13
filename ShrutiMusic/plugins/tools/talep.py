from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.enums import ParseMode
from ShrutiMusic import app
import random
from  datetime import datetime
import asyncio
import time

# --- EKLENTİ AYARLARI ---
# Destek taleplerini yönetecek yöneticinin (sudo) kullanıcı ID'si.
# Botun tüm talepleri ileteceği özel sohbet ID'sidir.
SUDO_ID = 7035704703  # LÜTFEN KENDİ TELEGRAM YÖNETİCİ ID'NİZLE DEĞİŞTİRİN!

# Durum Yönetimi (Gerçek botlarda veritabanı kullanılmalıdır - Firestore, MongoDB vb.)
# Bu sözlük, aktif taleplerin durumunu ve etkileşim mesajlarının ID'lerini tutar.
# Bot yeniden başlatılırsa bu veriler KAYBOLUR.
request_states = {}
request_counter = 0

def generate_request_id():
    """Basit ve benzersiz bir talep kimliği oluşturur."""
    global request_counter
    request_counter += 1
    # Unix zaman damgası + sayaç ile benzersizlik garanti edilir
    return f"REQ_{int(time.time())}_{request_counter}"

# --- YARDIMCI FONKSİYONLAR ---

def get_initial_keyboard():
    """Ana menü için başlangıç klavyesini oluşturur."""
    keyboard = [
        [
            types.InlineKeyboardButton("Öneri", callback_data="select_type|Öneri"),
            types.InlineKeyboardButton("Şikayet", callback_data="select_type|Şikayet"),
        ],
        [
            types.InlineKeyboardButton("Sorun/Hata", callback_data="select_type|Sorun/Hata"),
        ],
        [
            types.InlineKeyboardButton("Talep İptal", callback_data="cancel_request"),
        ],
    ]
    return types.InlineKeyboardMarkup(keyboard)

def get_awaiting_message_keyboard():
    """Kullanıcının mesajı beklenirken gösterilen klavye."""
    keyboard = [
        [
            types.InlineKeyboardButton("Talep İptal", callback_data="cancel_request"),
        ],
    ]
    return types.InlineKeyboardMarkup(keyboard)

def get_sudo_notification_keyboard(request_id, is_group):
    """Sudo'ya gönderilen ilk bildirim için klavye."""
    # Profiline Git veya Gruptaki Mesaja Git butonu
    profile_button_text = "Gruptaki Mesaja Git" if is_group else "Kullanıcı Profili"
    # NOT: Gerçek butonda 'url' parametresi veya bir yönlendirme mekanizması kullanılır.
    profile_callback = f"sudo_navigate|{request_id}" 
    
    keyboard = [
        [
            types.InlineKeyboardButton(profile_button_text, callback_data=profile_callback),
        ],
        [
            types.InlineKeyboardButton("Talebi Göster", callback_data=f"sudo_show|{request_id}"),
            types.InlineKeyboardButton("Talep İptal", callback_data=f"sudo_cancel|{request_id}"),
        ],
    ]
    return types.InlineKeyboardMarkup(keyboard)

def get_sudo_review_keyboard(request_id):
    """Sudo'ya tam talep gösterilirken kullanılan klavye."""
    keyboard = [
        [
            types.InlineKeyboardButton("Bot Üzerinden Yanıtla", callback_data=f"sudo_reply_init|{request_id}"),
            types.InlineKeyboardButton("Talep İptal", callback_data=f"sudo_cancel|{request_id}"),
        ],
    ]
    return types.InlineKeyboardMarkup(keyboard)

# --- PYROGRAM HANDLERS ---

# 1. /destek Komutu
@Client.on_message(filters.command("destek") & filters.private | filters.command("destek") & filters.group)
async def start_support(client: Client, message: types.Message):
    """Kullanıcı /destek yazdığında ana menüyü gönderir."""
    
    # Eğer kullanıcının aktif bir talebi varsa, tekrar başlatmayı engelle.
    for req_id, req_data in request_states.items():
        if req_data.get('user_id') == message.from_user.id and req_data.get('status') not in ['REPLIED', 'CANCELLED']:
            await message.reply_text(
                "Zaten aktif bir destek talebiniz mevcut. Lütfen mevcut talebinizin sonucunu bekleyin."
            )
            return

    text = "Deep Music destek kanalı ve lütfen talep türünüzü seçin."
    keyboard = get_initial_keyboard()
    
    # İlk mesajı gönder ve ID'sini sakla
    sent_message = await message.reply_text(text, reply_markup=keyboard, quote=True)

    # Geçici bir talep oluşturulur
    req_id = generate_request_id()
    request_states[req_id] = {
        'id': req_id,
        'user_id': message.from_user.id,        # Kullanıcının ID'si (PM göndermek için kullanılır)
        'chat_id': message.chat.id,             # Orijinal sohbet ID'si (Grup veya PM)
        'message_id': sent_message.id,          # Botun etkileşim mesajı ID'si
        'status': 'AWAITING_TYPE', 
    }
    
    print(f"[{req_id}] Yeni destek oturumu başlatıldı. Durum: AWAITING_TYPE")


# 2. Callback Query İşleyicisi
@Client.on_callback_query()
async def support_callback_handler(client: Client, callback_query: types.CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    message = callback_query.message
    
    # 2.1 Talep Tipi Seçimi (select_type|Öneri)
    if data.startswith("select_type|"):
        _, req_type = data.split("|")
        
        # Talep ID'sini bul
        req_id = next((k for k, v in request_states.items() if v.get('message_id') == message.id), None)
        
        if not req_id or request_states[req_id].get('user_id') != user_id or request_states[req_id].get('status') != 'AWAITING_TYPE':
            await callback_query.answer("Bu etkileşim süresi dolmuş veya size ait değil.", show_alert=True)
            return

        # Durumu güncelle: Talep tipi seçildi, mesaj bekleniyor
        request_states[req_id]['request_type'] = req_type
        request_states[req_id]['status'] = 'AWAITING_MESSAGE'
        
        text = f"Lütfen **{req_type}** talebinizi gönderin:"
        keyboard = get_awaiting_message_keyboard()
        
        await message.edit_text(text, reply_markup=keyboard)
        await callback_query.answer(f"Talep türü: {req_type} olarak ayarlandı.", show_alert=False)
        
        print(f"[{req_id}] Talep tipi seçildi: {req_type}. Durum: AWAITING_MESSAGE")
        
        
    # 2.2 Talep İptali (cancel_request, sudo_cancel)
    elif data.endswith("cancel_request") or data.startswith("sudo_cancel|"):
        
        req_id = None
        
        # Kullanıcı tarafı iptal (message.id ile talep ID'sini buluruz)
        if data == "cancel_request":
            req_id = next((k for k, v in request_states.items() if v.get('message_id') == message.id), None)
            
            if not req_id or request_states[req_id].get('user_id') != user_id:
                await callback_query.answer("Bu etkileşim size ait değil.", show_alert=True)
                return
                
            # Durum sadece CANCELLED olarak işaretlenir
            request_states[req_id]['status'] = 'CANCELLED'
            await message.edit_text("✅ Destek talebi başarıyla iptal edildi.", reply_markup=None)
            await callback_query.answer("Talep iptal edildi.", show_alert=False)
            print(f"[{req_id}] Kullanıcı tarafından iptal edildi.")

        # Sudo tarafı iptal (callback verisinden talep ID'sini çekeriz)
        elif data.startswith("sudo_cancel|"):
            _, req_id = data.split("|")
            
            if req_id not in request_states or user_id != SUDO_ID:
                await callback_query.answer("Bu talep bulunamadı veya size ait değil.", show_alert=True)
                return
            
            req_data = request_states[req_id]
            
            # Kullanıcıya iptal bilgisini gönder (user_id = PM chat id)
            await client.send_message(
                req_data['user_id'], # Kullanıcının PM ID'si
                "❌ **Önemli:** Sudo tarafından destek talebiniz iptal edilmiştir."
            )
            
            # Sudo'nun etkileşim mesajını güncelle
            await message.edit_text(
                f"❌ **Talep İptal Edildi**\n\nTalep Türü: {req_data.get('request_type', 'Bilinmiyor')}\nTalep Eden ID: `{req_data['user_id']}`",
                reply_markup=None
            )
            
            # Durumu güncelleyerek kaldır
            req_data['status'] = 'CANCELLED'

            await callback_query.answer("Talep başarıyla iptal edildi ve kullanıcıya bildirildi.", show_alert=True)
            print(f"[{req_id}] Sudo tarafından iptal edildi.")
            
            
    # 2.3 Sudo - Talebi Göster (sudo_show)
    elif data.startswith("sudo_show|"):
        _, req_id = data.split("|")
        
        if req_id not in request_states or user_id != SUDO_ID:
            await callback_query.answer("Bu talep bulunamadı veya yetkiniz yok.", show_alert=True)
            return

        req_data = request_states[req_id]
        
        # A. Kullanıcıya bildirim gönder (Talebiniz incelemeye alınmıştır)
        try:
            await client.send_message(
                chat_id=req_data['user_id'], # Kullanıcının PM ID'si
                text="ℹ️ **Talebiniz incelemeye alınmıştır.** En kısa sürede yanıtlanacaktır."
            )
        except Exception as e:
            print(f"Kullanıcıya 'incelemede' bildirimi gönderilemedi: {e}")
            
        # B. Sudo'nun etkileşim mesajını (bildirimi) düzenle
        await message.edit_text(
            f"✅ **Talep İncelemede**\n\n"
            f"Talep Türü: **{req_data['request_type']}**\n"
            f"Talep Eden ID: `{req_data['user_id']}`\n"
            f"Talep Edilen Saat: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
            reply_markup=None # İlk bildirimin butonları kaldırıldı
        )
        
        # C. Sudo'ya tam talebi göster
        review_text = (
            f"**Talebi Yanıtla - {req_data['request_type']}**\n\n"
            f"Kullanıcı ID: `{req_data['user_id']}`\n"
            f"Talep Mesajı:\n"
            "----------------------------------\n"
            f"*{req_data['message_text']}*"
        )
        keyboard = get_sudo_review_keyboard(req_id)
        
        sent_review_msg = await client.send_message(
            chat_id=user_id, # Sudo'nun özel sohbetine
            text=review_text,
            reply_markup=keyboard
        )
        
        # Durumu güncelle
        req_data['status'] = 'IN_REVIEW'
        req_data['sudo_review_msg_id'] = sent_review_msg.id
        await callback_query.answer("Talep incelemeye alındı.", show_alert=False)
        print(f"[{req_id}] Sudo talebi incelemeye aldı. Durum: IN_REVIEW")

        
    # 2.4 Sudo - Bot Üzerinden Yanıtla (sudo_reply_init)
    elif data.startswith("sudo_reply_init|"):
        _, req_id = data.split("|")
        
        if req_id not in request_states or user_id != SUDO_ID:
            await callback_query.answer("Bu talep bulunamadı veya yetkiniz yok.", show_alert=True)
            return

        req_data = request_states[req_id]
        
        # Sudo'nun etkileşim mesajını (tam talebin gösterildiği mesajı) düzenle
        await message.edit_text(
            f"📝 **{req_data['request_type']}** talebine yanıt bekleniyor.\n\n"
            f"Lütfen **yanıtınızı bir sonraki mesajınızda doğrudan** bu sohbete yazın. (Bu mesaja cevap vermeyin.)",
            reply_markup=None # Sadece metin bekleniyor
        )

        # Durumu güncelle: Sudo'dan mesaj bekleniyor
        req_data['status'] = 'AWAITING_SUDO_RESPONSE'
        # Bu mesajın ID'sini de saklayalım ki, yanıt geldiğinde düzenleyebilelim.
        req_data['sudo_review_msg_id'] = message.id 
        await callback_query.answer("Yanıtınız bekleniyor...", show_alert=False)
        print(f"[{req_id}] Sudo yanıt yazmaya başladı. Durum: AWAITING_SUDO_RESPONSE")

    # 2.5 Diğer Callback'ler (Profiline Git, Gruptaki Mesaja Git)
    elif data.startswith("sudo_navigate|"):
        # Burası bir URL veya gruptaki mesaj linki ile değiştirilmelidir.
        await callback_query.answer("Yönlendirme bağlantısı için talep ID'si kaydedildi.", show_alert=True)


# 3. Mesaj İşleyicisi (Kullanıcı Mesajı ve Sudo Yanıtı)
# Sadece özel sohbetlerdeki metin mesajlarını dinler.
@Client.on_message(filters.text & filters.private) 
async def process_user_and_sudo_message(client: Client, message: types.Message):
    user_id = message.from_user.id
    
    # --- A. KULLANICI TALEP MESAJI YAKALAMA ---
    
    # Kullanıcının aktif bir 'mesaj bekleniyor' durumu var mı kontrol et
    active_req_id = next((k for k, v in request_states.items() if v.get('user_id') == user_id and v.get('status') == 'AWAITING_MESSAGE'), None)
    
    if active_req_id:
        req_data = request_states[active_req_id]
        
        # Talep metnini kaydet
        req_data['message_text'] = message.text
        req_data['user_original_message_id'] = message.id
        req_data['status'] = 'MESSAGE_SENT'
        
        # 1. Kullanıcıya bildirim gönder: "Talebiniz alınmıştır"
        await client.send_message(
            chat_id=user_id,
            text="✅ **Talebiniz alınmıştır.** En kısa sürede Sudo tarafından incelenecektir."
        )

        # 2. Sudo'ya bildirim gönder: "Bir talep var"
        user_mention = message.from_user.mention or f"Kullanıcı (ID: `{user_id}`)"
        is_group = req_data['chat_id'] != user_id # Gruptan mı geldi kontrolü
        
        notification_text = (
            "🚨 **YENİ DESTEK TALEBİ VAR** 🚨\n\n"
            f"Talep Türü: **{req_data['request_type']}**\n"
            f"Talep Eden: {user_mention}\n"
            f"Talep Eden ID: `{user_id}`\n"
            f"Talep Edilen Saat: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        )
        
        keyboard = get_sudo_notification_keyboard(active_req_id, is_group)
        
        sudo_notif_msg = await client.send_message(
            chat_id=SUDO_ID,
            text=notification_text,
            reply_markup=keyboard
        )
        
        req_data['sudo_notif_msg_id'] = sudo_notif_msg.id
        
        # Kullanıcının ilk etkileşim mesajını sil (Talep tipinin seçildiği mesaj)
        try:
             await client.delete_messages(user_id, req_data['message_id'])
        except:
             pass # Silme yetkisi olmayabilir
             
        print(f"[{active_req_id}] Talep mesajı alındı. Durum: MESSAGE_SENT. Sudo'ya iletildi.")
        return
        
    # --- B. SUDO YANIT MESAJI YAKALAMA ---
    
    # Sudo'nun aktif bir 'yanıt bekleniyor' durumu var mı kontrol et
    if user_id == SUDO_ID:
        active_req_id = next((k for k, v in request_states.items() if v.get('status') == 'AWAITING_SUDO_RESPONSE'), None)
        
        if active_req_id:
            req_data = request_states[active_req_id]
            sudo_response_text = message.text
            
            # 1. Kullanıcıya yanıtı ilet (user_id = PM chat id)
            response_text = (
                f"✅ **Sudo Yanıtı ({req_data['request_type']} Talebiniz İçin):**\n"
                "----------------------------------\n"
                f"{sudo_response_text}"
            )
            
            await client.send_message(
                chat_id=req_data['user_id'],
                text=response_text
            )
            
            # 2. Sudo'nun etkileşim mesajını (bekleniyor mesajını) güncelle
            # NOT: Sudo'nun gönderdiği en son mesajın ID'si kullanılmalı.
            await client.edit_message_text(
                chat_id=user_id,
                message_id=req_data['sudo_review_msg_id'],
                text=f"✅ Yanıt başarıyla kullanıcıya iletilmiştir.\n\nYanıtınız:\n{sudo_response_text}",
                reply_markup=None
            )
            
            # 3. Durumu güncelle
            req_data['status'] = 'REPLIED'
            print(f"[{active_req_id}] Sudo yanıtı gönderdi. Durum: REPLIED. Kullanıcıya iletildi.")
            
            # Sudo'nun yazdığı mesajı silebiliriz (isteğe bağlı)
            try:
                await message.delete()
            except:
                pass 
                
            return

# --- EKLENTİ SONU ---
