from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import time
import re
from flask import Flask, jsonify
import threading
from pymongo import MongoClient

app = Flask(__name__)

# MongoDB setup
client = MongoClient("mongodb+srv://galeh:admin@cluster0.slk8m.mongodb.net/?retryWrites=true&w=majority")
db = client['telegram_bot']  # Database name
user_collection = db['users']  # Collection name for user data

# Constants
MENFES = "-1002486499773"
GRUP = "-1002441207941"
BOTLOGS = "-1002486499773"

def get_from_cache(user_id, key):
    user_data = user_collection.find_one({"user_id": user_id})
    if user_data:
        return user_data.get(key)
    return None

def set_value(user_id, key, value):
    user_collection.update_one({"user_id": user_id}, {"$set": {key: value}}, upsert=True)

def add_user(user_id):
    if not user_collection.find_one({"user_id": user_id}):
        user_collection.insert_one({"user_id": user_id, "baned": [], "admin": [6172467461], "jeda": False, "time": {}})

def clear_html(text):
    # Implement HTML clearing logic here
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

def check_hashtags(message):
    hashtags = ['#belial', '#tradeal']
    return any(tag in message for tag in hashtags)

def start(update: Update, context: CallbackContext):
    nama = update.message.from_user.first_name
    if update.message.from_user.last_name:
        nama += ' ' + update.message.from_user.last_name
    nama = clear_html(nama)

    add_user(update.message.from_user.id)  # Add user to the list

    pesan = f"Hai <b>{nama}!</b> 🐝\n\nPesan yang kamu kirim di sini,\nakan diteruskan secara otomatis\nke channel @Basedagangal ✨\n\nGunakan hashtag berikut agar\npesanmu terkirim:\n\n#belial #tradeal"
    update.message.reply_html(pesan)

def broadcast(update: Update, context: CallbackContext):
    user_data = user_collection.find_one({"user_id": update.message.from_user.id})

    # Check if the user is an admin
    if update.message.from_user.id not in user_data['admin']:
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    message = ' '.join(context.args)
    if not message:
        update.message.reply_text("Silahkan masukkan pesan yang ingin dibroadcast.")
        return

    # Check if there are users to send the message to
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

    # Styled response message
    reply_message = (
        f"<b>Pesan berhasil dikirim kepada {successful} pengguna.</b>"
        f"\n<i>Gagal mengirim pesan kepada {failed} pengguna.</i>"
    )

    update.message.reply_html(reply_message)

        
def handle_message(update: Update, context: CallbackContext):
    msgbot = update.message
    add_user(msgbot.from_user.id)  # Add user to the list
    step = get_from_cache(msgbot.from_user.id, 'step')
    if step:
        return

    nama = msgbot.from_user.first_name
    if msgbot.from_user.last_name:
        nama += ' ' + msgbot.from_user.last_name
    nama = clear_html(nama)

    if msgbot.chat.type == 'private':
        user_data = user_collection.find_one({"user_id": msgbot.from_user.id})
        bndat = user_data['baned']

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
                update.message.reply_html('Pesan berhasil terkirim!')
            else:
                update.message.reply_html(f"{nama}, pesanmu gagal terkirim silahkan gunakan hastag:\n\n#belial #tradeal")
    elif msgbot.text:
        if msgbot.chat.type == 'private':
            pola = re.compile(r'(#belial|#tradeal)', re.IGNORECASE)
            if pola.search(msgbot.text):
                user_data = user_collection.find_one({"user_id": msgbot.from_user.id})
                if user_data['jeda']:
                    update.message.reply_html("Saat ini tidak bisa mengirim pesan karena jeda diaktifkan.")
                    return

                c_time = int(time.time() * 1000)
                last_time = user_data['time'].get(f'last{msgbot.from_user.id}')

                if not last_time or (c_time - last_time > 3600000):
                    set_value(msgbot.from_user.id, f'time.last{msgbot.from_user.id}', c_time)

                    context.bot.copy_message(chat_id=MENFES, from_chat_id=msgbot.chat.id, message_id=msgbot.message_id, caption=msgbot.caption)
                    update.message.reply_html('Pesan berhasil terkirim!')

                    usn = f"@{msgbot.from_user.username}" if msgbot.from_user.username else "tidak ada username"
                    pesan_logs = f"<b>Nama :</b> {msgbot.from_user.first_name} (<code>{msgbot.from_user.id}</code>)\n<b>Username :</b><i> {usn}</i>\n<b>Pesan :</b> <i>{msgbot.text}</i>"
                    context.bot.send_message(chat_id=BOTLOGS, text=pesan_logs, parse_mode='HTML')
                else:
                    cw = c_time - last_time
                    wkttng = format_duration(3600000 - cw)
                    update.message.reply_html(f'Tunggu <b>{wkttng}</b> lagi, untuk mengirim pesan!')
            else:
                update.message.reply_html(f"{nama}, pesanmu gagal terkirim\n\nGunakan hashtag berikut agar pesanmu terkirim:\n#belial #tradeal", reply_to_message_id=msgbot.message_id)

def set_jeda(update: Update, context: CallbackContext):
    user_data = user_collection.find_one({"user_id": update.message.from_user.id})
    
    if update.message.from_user.id not in user_data['admin']:
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    if context.args and context.args[0].lower() in ['on', 'off']:
        set_value(update.message.from_user.id, 'jeda', context.args[0].lower() == 'on')
        status = "aktif" if context.args[0].lower() == 'on' else "nonaktif"
        update.message.reply_text(f"Fitur jeda sekarang {status}.")
    else:
        update.message.reply_text("Silakan masukkan 'on' atau 'off' untuk mengatur jeda.")

def ban_user(update: Update, context: CallbackContext):
    user_data = user_collection.find_one({"user_id": update.message.from_user.id})

    if update.message.from_user.id not in user_data['admin']:
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    if context.args:
        user_id = context.args[0]
        if user_id not in user_data['baned']:
            user_collection.update_one({"user_id": user_id}, {"$set": {"baned": user_data['baned'] + [user_id]}}, upsert=True)
            update.message.reply_text(f"Pengguna {user_id} telah diblokir.")
        else:
            update.message.reply_text(f"Pengguna {user_id} sudah diblokir.")
    else:
        update.message.reply_text("Silakan masukkan ID pengguna yang ingin diblokir.")

def reload_admins(update: Update, context: CallbackContext):
    try:
        # Fetch the chat member list from the channel
        members = context.bot.get_chat_administrators(MENFES)
        new_admins = [(member.user.id, member.user.username) for member in members]
        
        # Update the admin list in the user collection
        user_collection.update_one({"user_id": update.message.from_user.id}, {"$set": {"admin": [admin[0] for admin in new_admins]}}, upsert=True)
        
        # Create the admin list with clickable usernames
        admin_list = '\n'.join([f"<a href='tg://user?id={admin_id}'>{admin_name}</a>" for admin_id, admin_name in new_admins if admin_name])
        
        update.message.reply_html(
            f"<b>Daftar admin telah diperbarui:</b>\n{admin_list}"
        )
    except Exception as e:
        update.message.reply_text("Gagal memperbarui daftar admin.")
        print(f"Error while reloading admins: {e}")

@app.route('/')
def index():
    return jsonify({"message": "Bot is running! by @MzCoder"})

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def main():
    updater = Updater("YOUR_BOT_TOKEN", use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("setjeda", set_jeda))
    dp.add_handler(CommandHandler("ban", ban_user))
    dp.add_handler(CommandHandler("reload", reload_admins))
    dp.add_handler(MessageHandler(Filters.text | Filters.photo, handle_message))
    

    # Start the bot in a separate thread
    updater.start_polling()

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
