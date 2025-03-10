from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import time
from datetime import datetime, timedelta
import re
from flask import Flask, jsonify
import threading
from pymongo import MongoClient
import pytz

app = Flask(__name__)


MENFES = "-1001247979116"
GRUP = "-1001802952248"
BOTLOGS = "-1001386322689"
DEV = ""

# MongoDB setup
client = MongoClient("mongodb+srv://galeh:admin@cluster0.slk8m.mongodb.net/?retryWrites=true&w=majority")
db = client['telegram_bot']  # Database name
user_collection = db['users']  # Collection name for user data
global_collection = db['global']  # Collection name for global data
statistics_collection = db['statistics']  # Koleksi untuk menyimpan statistik
message_senders_collection = db['message_senders']  # Collection for mapping message IDs to user IDs


def save_message_sender(message_id, user_id):
    message_senders_collection.update_one(
        {"message_id": message_id},
        {"$set": {"user_id": user_id}},
        upsert=True  # Create a new document if it doesn't exist
    )

def get_user_id(message_id):
    # Query the message_senders collection to find the user ID for the given message ID
    result = message_senders_collection.find_one({"message_id": message_id})
    
    if result and 'user_id' in result:
        return result['user_id']  # Return the user ID if found
    else:
        print("User ID not found for the given message ID.")
        return None


def get_from_cache(user_id, key):
    user_data = user_collection.find_one({"user_id": user_id})
    if user_data:
        return user_data.get(key)
    return None

def set_value(user_id, key, value):
    user_collection.update_one({"user_id": user_id}, {"$set": {key: value}}, upsert=True)

def add_user(user_id):
    # Simpan data pengguna
    if not user_collection.find_one({"user_id": user_id}):
        user_collection.insert_one({
            "user_id": user_id,
            "time": {}
        })

    # Simpan data global jika belum ada
    if global_collection.count_documents({}) == 0:
        global_collection.insert_one({
            "jeda": False,
            "admin": [],
            "baned": []
        })



def update_statistics(user_id):
     # Mengatur zona waktu Jakarta
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    # Mendapatkan waktu saat ini di Jakarta
    today = datetime.now(jakarta_tz).strftime("%Y-%m-%d")  # Mendapatkan tanggal hari ini dalam format YYYY-MM-DD 
    statistics_collection.update_one(
        {"date": today},  # Mencocokkan statistik hari ini
        {
            "$inc": {"messages_sent": 1},  # Meningkatkan jumlah pesan
            "$addToSet": {"users": user_id}  # Menambahkan user_id ke daftar users (hanya unik)
        },
        upsert=True  # Buat dokumen jika tidak ada
    )

def reset_daily_statistics():
     # Mengatur zona waktu Jakarta
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    # Mendapatkan waktu saat ini di Jakarta
    today = datetime.now(jakarta_tz).strftime("%Y-%m-%d")  # Mendapatkan tanggal hari ini dalam format YYYY-MM-DD
    # Resetting or creating a new entry for today’s statistics
    statistics_collection.update_one(
        {"date": today},
        {"$set": {"messages_sent": 0, "users": []}},
        upsert=True
    )



def clear_html(text):
    return text

def format_duration(milliseconds):
    seconds = milliseconds // 1000 % 60
    minutes = (milliseconds // (1000 * 60)) % 60
    hours = (milliseconds // (1000 * 60 * 60)) % 24

    parts = []

    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")
    if seconds > 0:
        parts.append(f"{seconds} detik")

    return ', '.join(parts) or '0 detik'



def start(update: Update, context: CallbackContext):
    msgbot = update.message
    if msgbot.chat.type == 'private':

        sub = context.bot.get_chat_member(MENFES, msgbot.from_user.id)
        sub2 = context.bot.get_chat_member(GRUP, msgbot.from_user.id)

        if sub.status in ['left', 'kicked'] or sub2.status in ['left', 'kicked']:
            keyb = [
                [InlineKeyboardButton('Channel Base', url='https://t.me/Basedagangal'),
                 InlineKeyboardButton('Grup Base', url='https://t.me/sendbasedagangal2')],
                [InlineKeyboardButton('Coba Lagi', url='https://t.me/AUTOPOSTBASEDAGANGAL_BOT?start=')]
            ]
            update.message.reply_html("Tidak dapat diakses harap join terlebih dahulu", reply_markup=InlineKeyboardMarkup(keyb))
            return
            
    nama = update.message.from_user.first_name
    if update.message.from_user.last_name:
        nama += ' ' + update.message.from_user.last_name
    nama = clear_html(nama)

    add_user(update.message.from_user.id)

    pesan = f"Hai <b>{nama}!</b> 🐝\n\nPesan yang kamu kirim di sini,\nakan diteruskan secara otomatis\nke channel @Basedagangal ✨\n\nGunakan hashtag berikut agar\npesanmu terkirim:\n\n#belial #tradeal"
    update.message.reply_html(pesan)


# Fungsi untuk mendapatkan statistik
def show_statistics(update: Update, context: CallbackContext):    
    user_id = update.message.from_user.id

    # Cek apakah pengguna adalah admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    # Mendapatkan waktu saat ini di Jakarta
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    today = datetime.now(jakarta_tz).strftime("%Y-%m-%d")

    # Mengambil statistik hari ini
    stats = statistics_collection.find_one({"date": today})
    
    # Mengambil total statistik
    total_stats = statistics_collection.find_one({"total": True})
    total_messages = total_stats.get("total_messages", 0) if total_stats else 0 

    if stats:
        messages_sent_today = stats.get("messages_sent", 0)
        users_count_today = stats.get("users", [])
        total_users_today = len(users_count_today)

        # Menghitung pesan dalam 7 hari terakhir
        messages_last_7_days = sum(stat.get("messages_sent", 0) for stat in statistics_collection.find({
            "date": {"$gte": (datetime.now(jakarta_tz) - timedelta(days=7)).strftime("%Y-%m-%d")}
        }))

        total_users_last_7_days = set()
        for stat in statistics_collection.find({
            "date": {"$gte": (datetime.now(jakarta_tz) - timedelta(days=7)).strftime("%Y-%m-%d")}
        }):
            total_users_last_7_days.update(stat.get("users", []))

        # Menghitung pesan dalam 24 jam terakhir
        messages_last_24_hours = sum(stat.get("messages_sent", 0) for stat in statistics_collection.find({
            "date": {"$gte": (datetime.now(jakarta_tz) - timedelta(hours=24)).strftime("%Y-%m-%d")}
        }))

        total_users_last_24_hours = set()
        for stat in statistics_collection.find({
            "date": {"$gte": (datetime.now(jakarta_tz) - timedelta(hours=24)).strftime("%Y-%m-%d")}
        }):
            total_users_last_24_hours.update(stat.get("users", []))

        reply_message = (
            "<b>Statistik Hari Ini:</b>\n"
            f"Pesan Hari Ini: <code>{messages_sent_today}</code> Pesan\n"
            f"<b>Jumlah Pengguna</b>\n7 hari terakhir: <code>{len(total_users_last_7_days)}</code>\n"
            f"24 Jam Terakhir: <code>{len(total_users_last_24_hours)}</code>"
        )
    else:
        reply_message = "<b>Statistik Hari Ini:</b>\nTidak ada pesan yang dikirim hari ini."

    update.message.reply_html(reply_message)


def broadcast(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return
        
    users = list(user_collection.find())
    if not users:
        update.message.reply_text("Tidak ada pengguna yang terdaftar untuk dibroadcast.")
        return

    successful = 0
    failed = 0
    
    if update.message.reply_to_message:
        msgbot = update.message.reply_to_message
        for user in users:
            try:
                context.bot.copy_message(chat_id=user['user_id'], from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                successful += 1
            except Exception as e:
                failed += 1
                print(f"Failed to send message to {user['user_id']}: {e}")
                
            # Adding a delay to avoid hitting limits
            time.sleep(0.8)  # Adjust the delay as needed
    
    else:
        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Silahkan masukkan pesan/reply pesan yang ingin dibroadcast.")
            return

        for user in users:
            try:
                context.bot.send_message(chat_id=user['user_id'], text=message)
                successful += 1
            except Exception as e:
                failed += 1
                print(f"Failed to send message to {user['user_id']}: {e}")
                
            # Adding a delay to avoid hitting limits
            time.sleep(0.8)  # Adjust the delay as needed

    reply_message = (
        "<b>Status Broadcast:</b>\n"
        f"<b>✅ Berhasil Terkirim: </b><code>{successful} </code>\n"
        f"<b>❌ Gagal Mengirim Pesan Ke: </b><code>{failed}</code>"
    )

    update.message.reply_html(reply_message)


def handle_message(update: Update, context: CallbackContext):
    msgbot = update.message  # Ensure msgbot is assigned from update.message
    if msgbot is None:
        return  # Handle the case when msgbot is None

    if msgbot.chat.type == 'private':
        add_user(msgbot.from_user.id)
        global_data = global_collection.find_one({})
        if global_data and global_data.get("jeda"):
            update.message.reply_html("Saat Ini Tidak bisa Mengirim pesan.", reply_to_message_id=msgbot.message_id)
            return

        nama = msgbot.from_user.first_name
        if msgbot.from_user.last_name:
            nama += ' ' + msgbot.from_user.last_name
        nama = clear_html(nama)

        bndat = global_data.get('baned', [])
        if str(msgbot.from_user.id) in bndat:
            update.message.reply_html("🚫 Anda diblokir dari bot")
            return

        sub = context.bot.get_chat_member(MENFES, msgbot.from_user.id)
        sub2 = context.bot.get_chat_member(GRUP, msgbot.from_user.id)

        if sub.status in ['left', 'kicked'] or sub2.status in ['left', 'kicked']:
            keyb = [
                [InlineKeyboardButton('Channel Base', url='https://t.me/Basedagangal'),
                 InlineKeyboardButton('Grup Base', url='https://t.me/sendbasedagangal2')],
                [InlineKeyboardButton('Coba Lagi', url='https://t.me/AUTOPOSTBASEDAGANGAL_BOT?start=')]
            ]
            update.message.reply_html("Tidak dapat diakses harap join terlebih dahulu", reply_markup=InlineKeyboardMarkup(keyb))
            return

        if msgbot.photo:
            if msgbot.chat.type == 'private':
                pola = re.compile(r'(#belial|#tradeal)', re.IGNORECASE)
                if pola.search(msgbot.caption or ""):  # Ensure caption is checked correctly
                    message_sent = context.bot.copy_message(chat_id=MENFES, from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                    update.message.reply_html('Pesan berhasil terkirim!', reply_to_message_id=msgbot.message_id)
                    update_statistics(msgbot.from_user.id)
                    save_message_sender(message_sent.message_id, msgbot.from_user.id)
                else:
                    update.message.reply_html(f"{nama}, pesanmu gagal terkirim silahkan gunakan hastag:\n\n#belial #tradeal")
        elif msgbot.text:
            if msgbot.chat.type == 'private':
                pola = re.compile(r'(#belial|#tradeal)', re.IGNORECASE)
                if pola.search(msgbot.text):
                    user_data = user_collection.find_one({"user_id": msgbot.from_user.id})
                    if global_data and global_data.get('jeda'):
                        update.message.reply_html("Saat ini tidak bisa mengirim pesan karena jeda diaktifkan.")
                        return

                    c_time = int(time.time() * 1000)
                    last_time = user_data['time'].get(f'last{msgbot.from_user.id}') if user_data else None

                    if not last_time or (c_time - last_time > 3600000):
                        set_value(msgbot.from_user.id, f'time.last{msgbot.from_user.id}', c_time)

                        message_sent = context.bot.copy_message(chat_id=MENFES, from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                        update.message.reply_html('Pesan berhasil terkirim!', reply_to_message_id=msgbot.message_id)
                        update_statistics(msgbot.from_user.id)
                        save_message_sender(message_sent.message_id, msgbot.from_user.id)

                        usn = f"@{msgbot.from_user.username}" if msgbot.from_user.username else "tidak ada username"
                        pesan_logs = f"<b>Nama :</b> {msgbot.from_user.first_name} (<code>{msgbot.from_user.id}</code>)\n<b>Username :</b><i> {usn}</i>\n<b>Pesan :</b> <i>{msgbot.text}</i>"
                        context.bot.send_message(chat_id=BOTLOGS, text=pesan_logs, parse_mode='HTML')
                    else:
                        cw = c_time - last_time
                        wkttng = format_duration(3600000 - cw)
                        update.message.reply_html(f'Tunggu <b>{wkttng}</b> lagi, untuk mengirim pesan!')
                else:
                    update.message.reply_html(f"{nama}, pesanmu gagal terkirim silahkan gunakan hastag:\n#belial #tradeal", reply_to_message_id=msgbot.message_id)

    else:
        if msgbot.reply_to_message and msgbot.reply_to_message.forward_from_chat:
            original_id = msgbot.reply_to_message.forward_from_chat.id
            forward_message_id = msgbot.reply_to_message.forward_from_message_id

            if original_id == -1001247979116:
                if msgbot.from_user.id != 6559871796:
                    try:
                        sender_id = get_user_id(forward_message_id)
                        print(f"user id: {sender_id}")
                        context.bot.send_message(
                            chat_id=sender_id,
                            text=f"<b>Notifikasi</b> 🔔\nSeseorang mengomentari pesanmu: <a href='https://t.me/BASEDAGANGAL/{forward_message_id}?comment={msgbot.message_id}'>check komen</a>",
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    except Exception as error:
                        print(f"Error: {error}")

    

def set_jeda(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    # Ambil status jeda saat ini
    current_status = global_collection.find_one({}, {"jeda": 1})  # Mengambil status jeda
    is_jeda_active = current_status.get('jeda', False) if current_status else False

    # Buat tombol berdasarkan status jeda
    if is_jeda_active:
        keyboard = [[InlineKeyboardButton("Nonaktifkan Jeda", callback_data='jeda_off')]]
        update.message.reply_text("Fitur jeda saat ini aktif. Silakan pilih:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [[InlineKeyboardButton("Aktifkan Jeda", callback_data='jeda_on')]]
        update.message.reply_text("Fitur jeda saat ini nonaktif. Silakan pilih:", reply_markup=InlineKeyboardMarkup(keyboard))


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()  # Acknowledge the button press

    try:
        # Tentukan tindakan berdasarkan callback data
        if query.data == 'jeda_on':
            global_collection.update_one({}, {"$set": {"jeda": True}}, upsert=True)
            keyboard = [[InlineKeyboardButton("Nonaktifkan Jeda", callback_data='jeda_off')]]
            query.edit_message_text("Fitur jeda sekarang aktif untuk semua pengguna.", reply_markup=InlineKeyboardMarkup(keyboard))
           
        elif query.data == 'jeda_off':
            global_collection.update_one({}, {"$set": {"jeda": False}}, upsert=True)
            keyboard = [[InlineKeyboardButton("Aktifkan Jeda", callback_data='jeda_on')]]
            query.edit_message_text("Fitur jeda sekarang nonaktif untuk semua pengguna.", reply_markup=InlineKeyboardMarkup(keyboard))
    
    except Exception as e:
        # Menampilkan pesan kesalahan yang lebih informatif
        query.edit_message_text("Terjadi kesalahan saat mengubah status jeda. Silakan coba lagi.")
        print(f"Error while updating jeda status: {e}")  # Log kesalahan untuk debugging


def ban_user(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Periksa apakah pengguna adalah admin di global_collection
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    if context.args:
        user_to_ban = context.args[0]
        # Menambahkan user_id ke daftar baned di global_collection
        global_collection.update_one(
            {},
            {"$addToSet": {"baned": user_to_ban}},  # Menambahkan user_id ke daftar baned
            upsert=True  # Buat dokumen baru jika tidak ada
        )
        update.message.reply_text(f"Pengguna {user_to_ban} telah diblokir.")
    else:
        update.message.reply_text("Silakan masukkan ID pengguna yang ingin diblokir.")


def reload_admins(update: Update, context: CallbackContext):
    try:
        # Mengambil daftar administrator dari chat
        members = context.bot.get_chat_administrators(MENFES)
        new_admins = []
        
        for member in members:
            user_id = str(member.user.id)  # Mengambil ID pengguna sebagai string
            user_name = member.user.username if member.user.username else member.user.first_name
            new_admins.append((user_id, user_name))  # Menyimpan tuple (ID, Nama)

        # Tambahkan admin tetap
        permanent_admin_id = '5166575484'  # ID Developer
        if permanent_admin_id not in [admin[0] for admin in new_admins]:
            new_admins.append((permanent_admin_id, "Developer Bot"))

        # ID yang tidak dijadikan admin
        excluded_admin_id = '6821877639'  # ID AUTOPOSTBASEDAGANGAL_BOT
        new_admins = [admin for admin in new_admins if admin[0] != excluded_admin_id]

        # Mengupdate admin di global_collection
        global_data = global_collection.find_one({})
        if global_data is None:
            # Jika tidak ada data global, buat entri baru
            global_collection.insert_one({"admin": [admin[0] for admin in new_admins]})
        else:
            # Hanya simpan ID admin
            current_admins = global_data.get('admin', [])
            # Gabungkan daftar admin yang ada dengan yang baru, hilangkan duplikat
            updated_admins = list(set(current_admins + [admin[0] for admin in new_admins]))
            global_collection.update_one(
                {},
                {"$set": {"admin": updated_admins}}  # Mengupdate daftar admin
            )

        # Menyusun daftar admin untuk balasan
        admin_list = '\n'.join([
            f"{i + 1}. {admin[1]}"  # Menampilkan nama admin
            for i, admin in enumerate(new_admins)
        ])

        # Mengirim pesan dengan daftar admin yang telah diperbarui
        update.message.reply_text(
            f"<b>Daftar admin telah diperbarui:</b>\n{admin_list}",
            parse_mode="HTML"  # Menyertakan HTML untuk format teks
        )
    except Exception as e:
        update.message.reply_text("Gagal memperbarui daftar admin.")
        print(f"Kesalahan saat memuat ulang admin: {e}")


# Fungsi untuk memeriksa apakah pengguna adalah admin
def is_admin(user_id):
    global_data = global_collection.find_one({})
    if global_data and 'admin' in global_data:
        return str(user_id) in global_data['admin']  # Memeriksa apakah ID pengguna ada di daftar admin
    return False

def help_command(update: Update, context: CallbackContext):
    help_text = (
        "<b>Daftar Perintah:</b>\n\n"
        "<b>/start</b> - Memulai interaksi dengan bot.\n"
        "<b>/broadcast [pesan]/[reply pesan]</b> - Mengirim pesan ke semua pengguna terdaftar.\n"
        "<b>/jeda | /jeda_on | /jeda_off</b> - Mengatur jeda untuk pengiriman pesan.\n"
        "<b>/ban [user_id]</b> - Memblokir pengguna tertentu.\n"
        "<b>/reload</b> - Memperbarui daftar admin.\n"
        "<b>/stats</b> - Menampilkan statistik pengiriman pesan hari ini.\n"
        "<b>/help</b> - Menampilkan daftar perintah ini.\n\n"        
    )
    
    update.message.reply_html(help_text)

def jeda_on(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    global_collection.update_one({}, {"$set": {"jeda": True}}, upsert=True)
    update.message.reply_text("Fitur jeda sekarang aktif untuk semua pengguna.")

def jeda_off(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    global_collection.update_one({}, {"$set": {"jeda": False}}, upsert=True)
    update.message.reply_text("Fitur jeda sekarang nonaktif untuk semua pengguna.")



@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def main():
    #updater = Updater("6821877639:AAGEFkSaYVYaGiroIDFlnOSaKZ1wZxfQTL8", use_context=True)
    updater = Updater("7515743847:AAEu5xj47eIJ5blvKPIRZr0Va_e1w0JkLM8", use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("jeda", set_jeda))
    dp.add_handler(CommandHandler("jeda_on", jeda_on))
    dp.add_handler(CommandHandler("jeda_off", jeda_off))
    dp.add_handler(CommandHandler("ban", ban_user))
    dp.add_handler(CommandHandler("reload", reload_admins))
    dp.add_handler(CommandHandler("stats", show_statistics))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo, handle_message))
    dp.add_handler(CallbackQueryHandler(button))
    
    
    # Start the bot in a separate thread
    updater.start_polling()

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
