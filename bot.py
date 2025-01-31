from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import time
import re

# Constants
MENFES = "-1001247979116"
GRUP = "-1001802952248"
BOTLOGS = "-1001386322689"

# Sample database representation
userDB = {
    'set': json.dumps({
        'baned': [],
        'admin': [5166575484],  # Add your admin user ID here
        'jeda': None
    }),
    'time': json.dumps({}),
    'users': []  # Store user IDs who have interacted with the bot
}

def get_from_cache(user_id, key):
    # Implement caching logic here
    return None

def set_value(key, value):
    userDB[key] = value

def add_user(user_id):
    if user_id not in userDB['users']:
        userDB['users'].append(user_id)

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
    if update.message.from_user.id not in userDB['set']['admin']:
        update.message.reply_text("Hanya admin yang dapat menggunakan perintah ini.")
        return

    message = ' '.join(context.args)
    if not message:
        update.message.reply_text("Silahkan masukkan pesan yang ingin disiarkan.")
        return

    for user_id in userDB['users']:
        try:
            context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

    update.message.reply_text("Pesan berhasil disiarkan kepada semua pengguna.")

def handle_message(update: Update, context: CallbackContext):
    msgbot = update.message
    step = get_from_cache(msgbot.from_user.id, 'step')
    if step:
        return

    nama = msgbot.from_user.first_name
    if msgbot.from_user.last_name:
        nama += ' ' + msgbot.from_user.last_name
    nama = clear_html(nama)

    if msgbot.chat.type == 'private':
        dtset = json.loads(userDB['set'])
        bndat = dtset['baned']

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
                if dtset.get('jeda'):
                    update.message.reply_html("Saat Ini Tidak bisa Mengirim pesan")
                    return

                c_time = int(time.time() * 1000)
                last_time = json.loads(userDB['time']).get(f'last{msgbot.from_user.id}')

                if not last_time or (c_time - last_time > 3600000):
                    # Update last message time
                    data = json.loads(userDB['time'])
                    data[f'last{msgbot.from_user.id}'] = c_time
                    set_value('time', json.dumps(data))

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

def main():
    updater = Updater("6239054864:AAGrtQ4d9_lzH0eOrrUEmtAdpFWs8sw7I2c", use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))  # Adding the broadcast command
    dp.add_handler(MessageHandler(Filters.text | Filters.photo, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
