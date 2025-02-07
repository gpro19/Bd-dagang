from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import time
import datetime
import re
from flask import Flask, jsonify
import threading
from pymongo import MongoClient

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
    today = time.strftime("%Y-%m-%d")  # Mendapatkan tanggal hari ini dalam format YYYY-MM-DD
    statistics_collection.update_one(
        {"date": today},  # Mencocokkan statistik hari ini
        {
            "$inc": {"messages_sent": 1},  # Meningkatkan jumlah pesan
            "$addToSet": {"users": user_id}  # Menambahkan user_id ke daftar users (hanya unik)
        },
        upsert=True  # Buat dokumen jika tidak ada
    )

def reset_daily_statistics():
    today = time.strftime("%Y-%m-%d")
    # Resetting or creating a new entry for today’s statistics
    statistics_collection.update_one(
        {"date": today},
        {"$set": {"messages_sent": 0, "users": []}},
        upsert=True
    )


def is_admin(user_id):
    global_data = global_collection.find_one({})
    if global_data and 'admin' in global_data:
        return str(user_id) in global_data['admin']
    return False

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


def show_statistics(update: Update, context: CallbackContext):    
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not is_admin(user_id):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    today = time.strftime("%Y-%m-%d")
    stats = statistics_collection.find_one({"date": today})

    # Fetch total statistics
    total_stats = statistics_collection.find_one({"total": True})

    # Initialize total_messages to 0 if total_stats is None
    total_messages = total_stats.get("total_messages", 0) if total_stats else 0 

    if stats:
        messages_sent_today = stats.get("messages_sent", 0)
        users_count_today = stats.get("users", [])
        total_users_today = len(users_count_today)  # Total semua pengguna yang mengirim pesan hari ini

        # Menghitung pesan dalam 7 hari terakhir
        messages_last_7_days = sum(stat.get("messages_sent", 0) for stat in statistics_collection.find({
            "date": {"$gte": (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")}
        }))

        total_users_last_7_days = set()
        for stat in statistics_collection.find({
            "date": {"$gte": (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")}
        }):
            total_users_last_7_days.update(stat.get("users", []))

        # Menghitung pesan dalam 24 jam terakhir
        messages_last_24_hours = sum(stat.get("messages_sent", 0) for stat in statistics_collection.find({
            "date": {"$gte": (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d")}
        }))

        total_users_last_24_hours = set()
        for stat in statistics_collection.find({
            "date": {"$gte": (datetime.datetime.now() - datetime.timedelta(hours=24)).strftime("%Y-%m-%d")}
        }):
            total_users_last_24_hours.update(stat.get("users", []))

        reply_message = (
            "<b>Statistik Hari Ini:</b>\n"
            f"Pesan Hari Ini: <code>{messages_sent_today}</code> Pesan\n"
            f"Jumlah Pengguna Selama 7 Hari Terakhir: <code>{len(total_users_last_7_days)}</code>\n"
            f"Jumlah Pengguna Selama 24 Jam Terakhir: <code>{len(total_users_last_24_hours)}</code>"
        )
    else:
        reply_message = "<b>Statistik Hari Ini:</b>\nTidak ada pesan yang dikirim hari ini."

    update.message.reply_html(reply_message)


def broadcast(update: Update, context: CallbackContext):
    user_data = user_collection.find_one({"user_id": update.message.from_user.id})

    if update.message.from_user.id not in user_data.get('admin', []):
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    message = ' '.join(context.args)
    if not message:
        update.message.reply_text("Silahkan masukkan pesan yang ingin dibroadcast.")
        return

    users = list(user_collection.find())
    if not users:
        update.message.reply_text("Tidak ada pengguna yang terdaftar untuk dibroadcast.")
        return

    successful = 0
    failed = 0

    for user in users:
        try:
            context.bot.send_message(chat_id=user['user_id'], text=message)
            successful += 1
        except Exception as e:
            failed += 1
            print(f"Failed to send message to {user['user_id']}: {e}")
            context.bot.send_message(chat_id=user_data['admin'][0], text=f"Gagal mengirim pesan ke {user['user_id']}")
        
        # Adding a delay to avoid hitting limits
        time.sleep(0.5)  # Adjust the delay as needed

    reply_message = (
        "<b>Status Broadcast:</b>\n"
        f"<b>✅ Berhasil Terkirim: </b><code>{successful} </code>\n"
        f"<b>❌ Gagal Mengirim Pesan Ke: </b><code>{failed}</code>"
    )

    update.message.reply_html(reply_message)
    
def handle_message(update: Update, context: CallbackContext):
    msgbot = update.message
    add_user(msgbot.from_user.id)

    # Check if the 'jeda' feature is active for all users
    global_data = global_collection.find_one({})
    if global_data and global_data.get("jeda"):
        update.message.reply_html("Saat Ini Tidak bisa Mengirim pesan.", reply_to_message_id=msgbot.message_id)
        return

    nama = msgbot.from_user.first_name
    if msgbot.from_user.last_name:
        nama += ' ' + msgbot.from_user.last_name
    nama = clear_html(nama)

    if msgbot.chat.type == 'private':
        # Ambil daftar pengguna yang diblokir
        bndat = global_data.get('baned', [])

        # Periksa apakah pengguna diblokir
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
            if pola.search(msgbot.caption):
                context.bot.copy_message(chat_id=MENFES, from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                update.message.reply_html('Pesan berhasil terkirim!', reply_to_message_id=msgbot.message_id)
                update_statistics(msgbot.from_user.id)  # Update statistics
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
                last_time = user_data['time'].get(f'last{msgbot.from_user.id}')

                if not last_time or (c_time - last_time > 3600000):
                    set_value(msgbot.from_user.id, f'time.last{msgbot.from_user.id}', c_time)

                    context.bot.copy_message(chat_id=MENFES, from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                    update.message.reply_html('Pesan berhasil terkirim!', reply_to_message_id=msgbot.message_id)
                    update_statistics(msgbot.from_user.id)  # Update statistics

                    usn = f"@{msgbot.from_user.username}" if msgbot.from_user.username else "tidak ada username"
                    pesan_logs = f"<b>Nama :</b> {msgbot.from_user.first_name} (<code>{msgbot.from_user.id}</code>)\n<b>Username :</b><i> {usn}</i>\n<b>Pesan :</b> <i>{msgbot.text}</i>"
                    context.bot.send_message(chat_id=BOTLOGS, text=pesan_logs, parse_mode='HTML')
                else:
                    cw = c_time - last_time
                    wkttng = format_duration(3600000 - cw)
                    update.message.reply_html(f'Tunggu <b>{wkttng}</b> lagi, untuk mengirim pesan!')
            else:
                update.message.reply_html(f"{nama}, pesanmu gagal terkirim silahkan gunakan hastag:\n#belial #tradeal", reply_to_message_id=msgbot.message_id)    


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
        members = context.bot.get_chat_administrators(MENFES)
        new_admins = [
            member.user.username if member.user.username else member.user.first_name 
            for member in members
        ]  # Mengambil nama pengguna atau nama depan jika nama pengguna tidak ada

        # Tambahkan admin tetap
        permanent_admin_id = '5166575484'
        if permanent_admin_id not in new_admins:
            new_admins.append(permanent_admin_id)

        # Mengupdate admin di global_collection
        global_data = global_collection.find_one({})
        if global_data is None:
            # Jika tidak ada data global, buat baru
            global_collection.insert_one({"admin": new_admins})
        else:
            current_admins = global_data.get('admin', [])
            # Gabungkan daftar admin yang ada dengan yang baru, hilangkan duplikat
            updated_admins = list(set(current_admins + new_admins))
            global_collection.update_one(
                {},
                {"$set": {"admin": updated_admins}}  # Mengupdate daftar admin
            )
        
        admin_list = '\n'.join([f"{i + 1}. {admin_name}" for i, admin_name in enumerate(updated_admins)])

        update.message.reply_text(
            f"<b>Daftar admin telah diperbarui:</b>\n{admin_list}",
            parse_mode="HTML"  # Menyertakan HTML untuk format teks
        )
    except Exception as e:
        update.message.reply_text("Gagal memperbarui daftar admin.")
        print(f"Error while reloading admins: {e}")


def help_command(update: Update, context: CallbackContext):
    help_text = (
        "<b>Daftar Perintah:</b>\n\n"
        "<b>/start</b> - Memulai interaksi dengan bot.\n"
        "<b>/broadcast [pesan]</b> - Mengirim pesan ke semua pengguna terdaftar.\n"
        "<b>/jeda</b> - Mengatur status jeda untuk pengiriman pesan.\n"
        "<b>/ban [user_id]</b> - Memblokir pengguna tertentu.\n"
        "<b>/reload</b> - Memperbarui daftar admin dari grup.\n"
        "<b>/stats</b> - Menampilkan statistik pengiriman pesan hari ini.\n"
        "<b>/help</b> - Menampilkan daftar perintah ini.\n\n"        
    )
    
    update.message.reply_html(help_text)
    
    
@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def main():
    updater = Updater("6821877639:AAGEFkSaYVYaGiroIDFlnOSaKZ1wZxfQTL8", use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("jeda", set_jeda))
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
