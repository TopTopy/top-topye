# -*- coding: utf-8 -*-
"""
🤖 ربات SMS Bomber VIP - نسخه نهایی برای رندر
بات روی رندر، API روی لیارا
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
from datetime import datetime, date, timedelta
from flask import Flask, request
import os
import sys

# ==================== تنظیمات اصلی ====================

BOT_TOKEN = "8098018364:AAGcNlQ7SSOKewFdwRCUfz4PuA4PpRmcj3Y"
ADMIN_IDS = [7620484201, 8226091292]
REQUIRED_CHANNEL = "@death_star_sms_bomber"
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"

# اطلاعات سازنده
DEVELOPER_USERNAME = "top_topy_messenger_bot"  # یوزرنیم بات سازنده
DEVELOPER_ID = 8226091292  # آیدی عددی سازنده
SUPPORT_CHANNEL = "@death_star_sms_bomber"  # کانال پشتیبانی

# محدودیت‌های روزانه
NORMAL_LIMIT = 5     # کاربران عادی
VIP_LIMIT = 20       # کاربران ویژه

# آدرس سرور API روی لیارا
LIARA_API_URL = "https://deathstar-smsbomber-bot.liara.run"
API_TOKEN = "drdragon787_secret_token_2026"

# اسم سرویس رندر
SERVICE_NAME = "ftyydftrye5r-6e5te"
BASE_URL = f"https://{SERVICE_NAME}.onrender.com"
WEBHOOK_URL = f"{BASE_URL}/webhook"

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4", 
]

# ==================== مقداردهی اولیه ====================

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
user_processes = {}
support_tickets = {}  # برای ذخیره تیکت‌های پشتیبانی

# ==================== دیتابیس پیشرفته ====================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_protected_numbers()
    
    def create_tables(self):
        # جدول کاربران با اطلاعات کامل
        self.c.execute('''CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            last_reset_date TEXT,
            daily_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            vip_expiry TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT
        )''')
        
        # جدول شماره‌های مسدود
        self.c.execute('''CREATE TABLE blocked_phones (
            phone_hash TEXT PRIMARY KEY,
            date TEXT,
            reason TEXT,
            attempts INTEGER DEFAULT 0
        )''')
        
        # جدول آمار روزانه
        self.c.execute('''CREATE TABLE daily_stats (
            date TEXT PRIMARY KEY,
            total_requests INTEGER DEFAULT 0,
            vip_requests INTEGER DEFAULT 0,
            normal_requests INTEGER DEFAULT 0
        )''')
        
        # جدول تیکت‌های پشتیبانی
        self.c.execute('''CREATE TABLE support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            ticket_type TEXT,
            message TEXT,
            status TEXT DEFAULT 'باز',
            date TEXT,
            time TEXT,
            admin_response TEXT,
            response_date TEXT
        )''')
        
        # جدول لاگ استفاده
        self.c.execute('''CREATE TABLE usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_hash TEXT,
            date TEXT,
            time TEXT,
            success_count INTEGER,
            fail_count INTEGER,
            is_vip INTEGER
        )''')
        
        self.conn.commit()
    
    def add_protected_numbers(self):
        today = datetime.now().strftime('%Y-%m-%d')
        for h in PROTECTED_PHONE_HASHES:
            self.c.execute("INSERT OR IGNORE INTO blocked_phones VALUES (?, ?, ?, ?)", 
                          (h, today, "شماره محافظت شده", 0))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()
    
    def register_user(self, user_id, username, first_name, last_name=""):
        today = date.today().isoformat()
        self.c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, join_date, last_reset_date, daily_count, total_count, is_vip)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0)''',
            (user_id, username, first_name, last_name, today, today))
        self.conn.commit()
    
    def is_vip(self, user_id):
        self.c.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        if not result:
            return False
        is_vip, expiry = result
        if is_vip and expiry:
            if datetime.now().isoformat() > expiry:
                self.c.execute("UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE user_id = ?", (user_id,))
                self.conn.commit()
                return False
        return bool(is_vip)
    
    def set_vip(self, user_id, days=30, admin_id=None):
        expiry = (datetime.now() + timedelta(days=days)).isoformat()
        self.c.execute("UPDATE users SET is_vip = 1, vip_expiry = ? WHERE user_id = ?", (expiry, user_id))
        self.conn.commit()
        return True
    
    def remove_vip(self, user_id):
        self.c.execute("UPDATE users SET is_vip = 0, vip_expiry = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return True
    
    def get_vip_list(self):
        self.c.execute("SELECT user_id, username, first_name, vip_expiry FROM users WHERE is_vip = 1")
        return self.c.fetchall()
    
    def get_daily_count(self, user_id):
        today = date.today().isoformat()
        self.c.execute("SELECT daily_count, last_reset_date FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        if not result:
            return 0
        count, last_reset = result
        if last_reset != today:
            self.c.execute("UPDATE users SET daily_count = 0, last_reset_date = ? WHERE user_id = ?", (today, user_id))
            self.conn.commit()
            return 0
        return count
    
    def increment_usage(self, user_id, success, fail):
        today = date.today().isoformat()
        now = datetime.now().strftime('%H:%M:%S')
        
        # آپدیت آمار کاربر
        self.c.execute('''UPDATE users SET 
            daily_count = daily_count + 1,
            total_count = total_count + 1
            WHERE user_id = ?''', (user_id,))
        
        # ثبت لاگ
        phone_hash = "unknown"
        is_vip = 1 if self.is_vip(user_id) else 0
        
        self.c.execute('''INSERT INTO usage_logs 
            (user_id, phone_hash, date, time, success_count, fail_count, is_vip)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone_hash, today, now, success, fail, is_vip))
        
        # آپدیت آمار کلی
        self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, total_requests, vip_requests, normal_requests)
            VALUES (?, 
                COALESCE((SELECT total_requests + 1 FROM daily_stats WHERE date = ?), 1),
                COALESCE((SELECT vip_requests + ? FROM daily_stats WHERE date = ?), ?),
                COALESCE((SELECT normal_requests + ? FROM daily_stats WHERE date = ?), ?)
            )''', 
            (today, today, 1 if is_vip else 0, today, 1 if is_vip else 0,
             1 if not is_vip else 0, today, 1 if not is_vip else 0))
        
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        self.c.execute("SELECT total_count, join_date, is_vip, vip_expiry FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        if not result:
            return 0, "نامشخص", False, None
        return result
    
    def get_global_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        total_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        vip_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT SUM(total_requests) FROM daily_stats")
        total_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT SUM(vip_requests) FROM daily_stats")
        vip_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT date, total_requests, vip_requests, normal_requests FROM daily_stats ORDER BY date DESC LIMIT 7")
        weekly = self.c.fetchall()
        
        return {
            "total_users": total_users,
            "vip_users": vip_users,
            "total_requests": total_requests,
            "vip_requests": vip_requests,
            "normal_requests": total_requests - vip_requests,
            "weekly": weekly
        }
    
    def is_phone_protected(self, phone):
        h = hashlib.sha256(phone.encode()).hexdigest()
        self.c.execute("SELECT * FROM blocked_phones WHERE phone_hash = ?", (h,))
        result = self.c.fetchone()
        if result:
            self.c.execute("UPDATE blocked_phones SET attempts = attempts + 1 WHERE phone_hash = ?", (h,))
            self.conn.commit()
            return True
        return False
    
    # توابع پشتیبانی
    def add_ticket(self, user_id, username, ticket_type, message):
        today = date.today().isoformat()
        now = datetime.now().strftime('%H:%M:%S')
        self.c.execute('''INSERT INTO support_tickets 
            (user_id, username, ticket_type, message, status, date, time)
            VALUES (?, ?, ?, ?, 'باز', ?, ?)''',
            (user_id, username, ticket_type, message, today, now))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_user_tickets(self, user_id):
        self.c.execute('''SELECT id, ticket_type, message, status, date, time, admin_response 
                         FROM support_tickets WHERE user_id = ? ORDER BY id DESC''', (user_id,))
        return self.c.fetchall()
    
    def get_all_tickets(self, status=None):
        if status:
            self.c.execute('''SELECT id, user_id, username, ticket_type, message, status, date, time 
                            FROM support_tickets WHERE status = ? ORDER BY id DESC''', (status,))
        else:
            self.c.execute('''SELECT id, user_id, username, ticket_type, message, status, date, time 
                            FROM support_tickets ORDER BY id DESC''')
        return self.c.fetchall()
    
    def respond_to_ticket(self, ticket_id, response):
        now = datetime.now().isoformat()
        self.c.execute('''UPDATE support_tickets 
                         SET status = 'پاسخ داده شده', admin_response = ?, response_date = ?
                         WHERE id = ?''', (response, now, ticket_id))
        self.conn.commit()
    
    def close_ticket(self, ticket_id):
        self.c.execute("UPDATE support_tickets SET status = 'بسته شده' WHERE id = ?", (ticket_id,))
        self.conn.commit()

# ایجاد دیتابیس
db = Database()

# ==================== توابع کمکی ====================

def hash_phone(phone):
    return hashlib.sha256(phone.encode()).hexdigest()

def mask_phone(phone):
    return phone[:4] + "****" + phone[-4:]

def is_admin(user_id):
    return user_id in ADMIN_IDS or (db.get_user(user_id) and db.get_user(user_id)[10] == 1)

def is_developer(user_id):
    return user_id == DEVELOPER_ID

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

def check_daily_limit(user_id):
    if is_admin(user_id):
        return True, 0, "ادمین"
    
    daily = db.get_daily_count(user_id)
    
    if db.is_vip(user_id):
        return daily < VIP_LIMIT, daily, "VIP"
    else:
        return daily < NORMAL_LIMIT, daily, "عادی"

# ==================== توابع API ====================

def get_random_ua():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/112.0.0.0 Mobile Safari/537.36",
    ]
    return random.choice(agents)

def send_request_to_liara(phone):
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "phone": phone,
            "timestamp": time.time(),
            "request_id": random.randint(1000, 9999)
        }
        
        response = requests.post(
            f"{LIARA_API_URL}/api/bomb",
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return True, result.get("success", 0), result.get("fail", 0), result
        else:
            return False, 0, 0, {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"❌ خطا در ارتباط با لیارا: {e}")
        return False, 0, 0, {"error": str(e)}

# ==================== صفحات وب ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    """دریافت آپدیت از تلگرام - با دیباگ کامل"""
    print("="*60)
    print(f"📩 Webhook called at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📌 Remote IP: {request.remote_addr}")
    print(f"📌 Headers: {dict(request.headers)}")
    
    try:
        json_str = request.get_data().decode('UTF-8')
        print(f"📨 Data received: {json_str[:500]}...")
        
        if not json_str:
            print("⚠️ Empty data received")
            return 'Empty', 400
        
        update = telebot.types.Update.de_json(json_str)
        print(f"✅ Update ID: {update.update_id}")
        
        bot.process_new_updates([update])
        print("✅ Update processed successfully")
        
        return 'OK', 200
    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        import traceback
        traceback.print_exc()
        return 'Error', 500

@app.route('/')
def home():
    stats = db.get_global_stats()
    return f"""
    <html>
        <head>
            <title>ربات SMS Bomber VIP</title>
            <style>
                body {{ 
                    font-family: 'Vazir', Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    margin: 0;
                    min-height: 100vh;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    padding: 40px;
                    border-radius: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1 {{ color: #ffd700; }}
                .developer {{ 
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
                .stat-card {{
                    background: rgba(255,255,255,0.2);
                    padding: 20px;
                    border-radius: 10px;
                }}
                .vip {{ color: #ffd700; }}
                .normal {{ color: #4CAF50; }}
                .contact {{
                    background: rgba(0,0,0,0.3);
                    padding: 20px;
                    border-radius: 10px;
                    margin-top: 30px;
                }}
                a {{ color: #ffd700; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 ربات SMS Bomber VIP</h1>
                
                <div class="developer">
                    <h2>👨‍💻 سازنده: @{DEVELOPER_USERNAME}</h2>
                    <p>📢 کانال پشتیبانی: {SUPPORT_CHANNEL}</p>
                    <p>🤖 بات ارتباطی: <a href="https://t.me/{DEVELOPER_USERNAME}">@{DEVELOPER_USERNAME}</a></p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>👥 کل کاربران</h3>
                        <h2>{stats['total_users']}</h2>
                    </div>
                    <div class="stat-card">
                        <h3 class="vip">💎 VIP</h3>
                        <h2 class="vip">{stats['vip_users']}</h2>
                    </div>
                    <div class="stat-card">
                        <h3>📊 کل درخواست</h3>
                        <h2>{stats['total_requests']}</h2>
                    </div>
                </div>
                
                <p>🔰 کاربران عادی: {NORMAL_LIMIT} بار در روز</p>
                <p class="vip">💎 کاربران VIP: {VIP_LIMIT} بار در روز</p>
                
                <div class="contact">
                    <h3>📞 ارتباط با سازنده</h3>
                    <p>برای ارتباط مستقیم با سازنده، از ربات استفاده کنید:</p>
                    <p>👉 دکمه 📞 پشتیبانی در منوی ربات</p>
                    <p>🤖 یا مستقیم به <a href="https://t.me/{DEVELOPER_USERNAME}">@{DEVELOPER_USERNAME}</a> پیام دهید</p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "developer": f"@{DEVELOPER_USERNAME}",
        "developer_bot": f"https://t.me/{DEVELOPER_USERNAME}",
        "support": SUPPORT_CHANNEL,
        "liara_api": LIARA_API_URL,
        "time": datetime.now().isoformat()
    }

@app.route('/webhook-status')
def webhook_status():
    try:
        info = bot.get_webhook_info()
        return {
            "ok": info.url == WEBHOOK_URL,
            "current_url": info.url,
            "correct_url": WEBHOOK_URL,
            "is_correct": info.url == WEBHOOK_URL,
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ==================== تنظیم Webhook ====================

def set_webhook():
    try:
        print(f"📌 تنظیم Webhook روی {WEBHOOK_URL}")
        bot.remove_webhook()
        time.sleep(2)
        result = bot.set_webhook(url=WEBHOOK_URL)
        if result:
            print(f"✅ Webhook با موفقیت تنظیم شد")
            return True
    except Exception as e:
        print(f"❌ خطا: {e}")
    return False

# ==================== هندلرهای بات ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    db.register_user(user_id, username, first_name, last_name)
    
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🚀 شروع بمباران"))
    markup.add(KeyboardButton("📊 راهنما"), KeyboardButton("📊 آمار من"))
    markup.add(KeyboardButton("📞 پشتیبانی"), KeyboardButton("💎 وضعیت VIP"))
    
    if db.is_vip(user_id):
        markup.add(KeyboardButton("💎 پنل VIP"))
    
    if is_admin(user_id):
        markup.add(KeyboardButton("👑 پنل مدیریت"))
    
    welcome = (
        "🤖 **به ربات SMS Bomber خوش آمدید!**\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"🤖 **بات ارتباطی:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال پشتیبانی:** {SUPPORT_CHANNEL}\n\n"
        f"📌 **محدودیت روزانه:**\n"
        f"• کاربران عادی: {NORMAL_LIMIT} بار\n"
        f"• کاربران VIP: {VIP_LIMIT} بار 💎\n\n"
        f"📢 **کانال اجباری:** {REQUIRED_CHANNEL}\n\n"
        "🚀 برای شروع از دکمه زیر استفاده کنید:"
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

# ==================== بخش پشتیبانی ====================

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support_menu(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📨 ارسال پیام به سازنده", callback_data="support_message"),
        InlineKeyboardButton("📋 تیکت‌های من", callback_data="my_tickets"),
        InlineKeyboardButton("👨‍💻 تماس مستقیم", url=f"https://t.me/{DEVELOPER_USERNAME}"),
        InlineKeyboardButton("📢 کانال", url=CHANNEL_LINK)
    )
    
    text = (
        "📞 **مرکز پشتیبانی**\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"🤖 **بات ارتباطی:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال:** {SUPPORT_CHANNEL}\n\n"
        "از طریق گزینه‌های زیر می‌توانید با ما در ارتباط باشید:"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "support_message")
def support_message_callback(call):
    msg = bot.send_message(call.message.chat.id, 
        "📨 **ارسال پیام به سازنده**\n\n"
        "لطفاً پیام خود را ارسال کنید. سازنده در اولین فرصت پاسخ خواهد داد.\n"
        "(میتوانید سوال، پیشنهاد یا مشکل خود را بنویسید)")
    bot.register_next_step_handler(msg, process_support_message)

def process_support_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "بدون یوزرنیم"
    text = message.text
    
    # ثبت تیکت در دیتابیس
    ticket_id = db.add_ticket(user_id, username, "پیام کاربر", text)
    
    # ارسال به ادمین‌ها
    for admin_id in ADMIN_IDS:
        try:
            admin_msg = (
                f"📨 **تیکت جدید از کاربر**\n\n"
                f"🆔 آیدی: `{user_id}`\n"
                f"👤 یوزرنیم: @{username}\n"
                f"📝 پیام: {text}\n"
                f"🎫 شماره تیکت: {ticket_id}\n\n"
                f"برای پاسخ از دستور /reply {ticket_id} استفاده کنید."
            )
            bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
        except:
            pass
    
    bot.send_message(message.chat.id, 
        "✅ **پیام شما با موفقیت ارسال شد!**\n"
        "سازنده در اولین فرصت پاسخ خواهد داد.", 
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "my_tickets")
def my_tickets_callback(call):
    tickets = db.get_user_tickets(call.from_user.id)
    
    if not tickets:
        bot.send_message(call.message.chat.id, "📭 شما هیچ تیکتی ندارید.")
        return
    
    text = "📋 **لیست تیکت‌های شما:**\n\n"
    for ticket in tickets:
        ticket_id, t_type, msg, status, date, time, response = ticket
        status_emoji = "🟢" if status == "باز" else "🔴" if status == "بسته شده" else "🟡"
        text += f"{status_emoji} **تیکت #{ticket_id}**\n"
        text += f"📅 {date} {time}\n"
        text += f"📝 {msg[:50]}...\n"
        if response:
            text += f"💬 پاسخ: {response[:50]}...\n"
        text += "─────────────\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# دستور پاسخ به تیکت (فقط برای ادمین)
@bot.message_handler(commands=['reply'])
def reply_to_ticket(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ دسترسی ندارید!")
        return
    
    try:
        parts = message.text.split()
        ticket_id = int(parts[1])
        response = ' '.join(parts[2:])
        
        if not response:
            bot.reply_to(message, "❌ لطفاً متن پاسخ را هم وارد کنید.\nمثال: /reply 5 ممنون از پیامت")
            return
        
        db.respond_to_ticket(ticket_id, response)
        
        # پیدا کردن کاربر و ارسال پاسخ
        conn = sqlite3.connect(':memory:')
        c = conn.cursor()
        c.execute("SELECT user_id FROM support_tickets WHERE id = ?", (ticket_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            user_id = result[0]
            try:
                bot.send_message(user_id,
                    f"📨 **پاسخ به تیکت #{ticket_id}**\n\n"
                    f"💬 {response}\n\n"
                    f"با تشکر از شما - تیم پشتیبانی",
                    parse_mode="Markdown")
            except:
                pass
        
        bot.reply_to(message, f"✅ پاسخ به تیکت {ticket_id} ارسال شد!")
        
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ فرمت صحیح: /reply [شماره تیکت] [متن پاسخ]")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# ==================== ادامه هندلرها ====================

@bot.message_handler(func=lambda m: m.text == "🚀 شروع بمباران")
@membership_required
def ask_phone(message):
    user_id = message.from_user.id
    
    can_use, daily, user_type = check_daily_limit(user_id)
    limit = VIP_LIMIT if user_type == "VIP" else NORMAL_LIMIT
    
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {daily} بار استفاده کرده‌اید.\n"
            f"محدودیت {'VIP' if user_type == 'VIP' else 'عادی'} {limit} بار است.\n"
            "فردا دوباره تلاش کنید."
        )
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست.")
        return
    
    msg = bot.send_message(message.chat.id, "📱 شماره موبایل را وارد کنید (مثال: 09123456789):")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    phone = message.text.strip().replace(" ", "")
    
    if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
        bot.send_message(chat_id, "❌ شماره نامعتبر است.")
        return
    
    if db.is_phone_protected(phone):
        bot.send_message(chat_id, "❌ این شماره در لیست سیاه قرار دارد.")
        return
    
    remaining = VIP_LIMIT - db.get_daily_count(user_id) if db.is_vip(user_id) else NORMAL_LIMIT - db.get_daily_count(user_id)
    user_type = "VIP" if db.is_vip(user_id) else "عادی"
    
    bot.send_message(chat_id, f"✅ امروز {remaining} بار دیگر می‌توانید استفاده کنید. (نوع: {user_type})")
    
    user_processes[chat_id] = True
    msg = bot.send_message(chat_id, f"🔰 شروع برای {mask_phone(phone)}...\n🔄 در حال اتصال به سرور لیارا...")
    
    thread = threading.Thread(target=bombing_process, args=(chat_id, user_id, phone, msg.message_id))
    thread.daemon = True
    thread.start()

def bombing_process(chat_id, user_id, phone, msg_id):
    try:
        success, success_count, fail_count, details = send_request_to_liara(phone)
        
        if success:
            db.increment_usage(user_id, success_count, fail_count)
            
            total = success_count + fail_count
            rate = int(success_count / total * 100) if total > 0 else 0
            user_type = "VIP 💎" if db.is_vip(user_id) else "عادی 👤"
            remaining = VIP_LIMIT - db.get_daily_count(user_id) if db.is_vip(user_id) else NORMAL_LIMIT - db.get_daily_count(user_id)
            
            bot.edit_message_text(
                f"✅ **پایان فرآیند**\n\n"
                f"📱 **شماره:** {mask_phone(phone)}\n"
                f"👤 **نوع کاربر:** {user_type}\n"
                f"✅ **موفق:** {success_count}\n"
                f"❌ **ناموفق:** {fail_count}\n"
                f"📊 **نرخ موفقیت:** {rate}%\n"
                f"🔰 **باقیمانده امروز:** {remaining}\n"
                f"🌐 **سرور:** لیارا",
                chat_id, msg_id,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                f"❌ **خطا در اتصال به سرور لیارا**\n\n"
                f"📱 **شماره:** {mask_phone(phone)}\n"
                f"⚠️ **خطا:** {details.get('error', 'نامشخص')}\n\n"
                f"🔄 لطفاً دوباره تلاش کنید.",
                chat_id, msg_id,
                parse_mode="Markdown"
            )
    except Exception as e:
        bot.edit_message_text(
            f"❌ **خطا:** {str(e)[:100]}",
            chat_id, msg_id
        )
    finally:
        user_processes.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_message(message):
    user_type = "VIP 💎" if db.is_vip(message.from_user.id) else "عادی 👤"
    limit = VIP_LIMIT if db.is_vip(message.from_user.id) else NORMAL_LIMIT
    
    text = (
        "📚 **راهنمای استفاده**\n\n"
        "1️⃣ روی دکمه **🚀 شروع بمباران** کلیک کنید\n"
        "2️⃣ شماره موبایل را وارد کنید\n"
        "3️⃣ منتظر بمانید\n\n"
        f"👤 **نوع کاربر:** {user_type}\n"
        f"📊 **محدودیت:** {limit} بار در روز\n"
        f"🔰 **تعداد APIها:** 100+ (روی لیارا)\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"🤖 **بات ارتباطی:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال پشتیبانی:** {SUPPORT_CHANNEL}\n\n"
        "💎 **برای دریافت VIP با ادمین تماس بگیرید**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def my_stats(message):
    user_id = message.from_user.id
    daily = db.get_daily_count(user_id)
    total, join_date, is_vip, vip_expiry = db.get_user_stats(user_id)
    limit = VIP_LIMIT if is_vip else NORMAL_LIMIT
    remaining = limit - daily
    
    status = "👑 ادمین" if is_admin(user_id) else ("💎 VIP" if is_vip else "👤 کاربر عادی")
    
    text = (
        f"📊 **آمار شما**\n\n"
        f"🆔 **آیدی:** `{user_id}`\n"
        f"👤 **نوع:** {status}\n"
        f"📅 **عضویت:** {join_date}\n"
        f"📊 **امروز:** {daily}/{limit}\n"
        f"✅ **باقیمانده:** {remaining}\n"
        f"🔰 **کل استفاده:** {total}"
    )
    
    if is_vip and vip_expiry:
        expiry_date = vip_expiry.split('T')[0]
        text += f"\n⏳ **انقضای VIP:** {expiry_date}"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💎 وضعیت VIP")
def vip_status(message):
    user_id = message.from_user.id
    if db.is_vip(user_id):
        daily = db.get_daily_count(user_id)
        remaining = VIP_LIMIT - daily
        _, _, _, expiry = db.get_user_stats(user_id)
        expiry_date = expiry.split('T')[0] if expiry else "نامشخص"
        
        text = (
            "💎 **وضعیت VIP شما**\n\n"
            "✅ شما کاربر ویژه هستید\n"
            f"📊 محدودیت شما: {VIP_LIMIT} بار در روز\n"
            f"📊 استفاده امروز: {daily}/{VIP_LIMIT}\n"
            f"✅ باقیمانده: {remaining}\n"
            f"⏳ تاریخ انقضا: {expiry_date}\n\n"
            "🔰 مزایا: محدودیت بالاتر، پشتیبانی優先"
        )
    else:
        text = (
            "💎 **دریافت VIP**\n\n"
            "با دریافت VIP می‌توانید:\n"
            f"• روزانه {VIP_LIMIT} بار استفاده کنید\n"
            "• به APIهای ویژه دسترسی دارید\n"
            "• پشتیبانی優先\n\n"
            f"برای دریافت با ادمین تماس بگیرید: @{DEVELOPER_USERNAME}"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💎 پنل VIP")
def vip_panel(message):
    if not db.is_vip(message.from_user.id) and not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ این بخش فقط برای کاربران VIP است!")
        return
    
    text = (
        "💎 **پنل VIP**\n\n"
        f"✅ شما کاربر ویژه هستید\n"
        f"📊 محدودیت شما: {VIP_LIMIT} بار در روز\n"
        f"🔰 دسترسی به همه APIها\n"
        f"⚡ پشتیبانی優先\n\n"
        "برای اطلاعات بیشتر با ادمین تماس بگیرید."
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ دسترسی غیرمجاز!")
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"),
        InlineKeyboardButton("💎 مدیریت VIP", callback_data="admin_vip"),
        InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list"),
        InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add"),
        InlineKeyboardButton("➖ حذف VIP", callback_data="vip_remove"),
        InlineKeyboardButton("📨 تیکت‌ها", callback_data="admin_tickets"),
        InlineKeyboardButton("🔄 ریست Webhook", callback_data="admin_webhook")
    )
    
    stats = db.get_global_stats()
    tickets = db.get_all_tickets('باز')
    
    text = (
        "👑 **پنل مدیریت**\n\n"
        f"📊 **آمار کلی:**\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"💎 VIP: {stats['vip_users']}\n"
        f"📊 کل درخواست: {stats['total_requests']}\n"
        f"💎 درخواست VIP: {stats['vip_requests']}\n"
        f"👤 درخواست عادی: {stats['normal_requests']}\n\n"
        f"📨 تیکت‌های باز: {len(tickets)}\n"
        f"🔗 **وضعیت لیارا:** {LIARA_API_URL}"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('admin_', 'vip_')))
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    if call.data == "admin_stats":
        stats = db.get_global_stats()
        text = "📊 **آمار کلی**\n\n"
        text += f"👥 کل کاربران: {stats['total_users']}\n"
        text += f"💎 VIP: {stats['vip_users']}\n"
        text += f"📊 کل درخواست: {stats['total_requests']}\n"
        text += f"💎 درخواست VIP: {stats['vip_requests']}\n"
        text += f"👤 درخواست عادی: {stats['normal_requests']}\n\n"
        text += "📈 **آمار هفتگی:**\n"
        for day in stats['weekly']:
            text += f"  • {day[0]}: {day[1]} کل ({day[2]} VIP)\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "admin_vip":
        vips = db.get_vip_list()
        if vips:
            text = "💎 **لیست کاربران VIP:**\n\n"
            for vip in vips:
                user_id, username, first_name, expiry = vip
                expiry_date = expiry.split('T')[0] if expiry else "نامشخص"
                text += f"• {first_name} - `{user_id}` (@{username})\n  ⏳ انقضا: {expiry_date}\n\n"
        else:
            text = "📭 هیچ کاربر VIP وجود ندارد"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "vip_list":
        vips = db.get_vip_list()
        if vips:
            text = "📋 **لیست VIP:**\n\n"
            for vip in vips:
                user_id, username, first_name, expiry = vip
                expiry_date = expiry.split('T')[0] if expiry else "نامشخص"
                text += f"• {first_name} - `{user_id}`\n  ⏳ {expiry_date}\n"
        else:
            text = "📭 لیست خالی است"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "vip_add":
        msg = bot.send_message(call.message.chat.id, 
            "➕ **افزودن کاربر VIP**\n\n"
            "لطفاً آیدی عددی کاربر را وارد کنید:\n"
            "(مثال: 123456789)")
        bot.register_next_step_handler(msg, process_vip_add)
    
    elif call.data == "vip_remove":
        msg = bot.send_message(call.message.chat.id,
            "➖ **حذف VIP کاربر**\n\n"
            "لطفاً آیدی عددی کاربر را وارد کنید:")
        bot.register_next_step_handler(msg, process_vip_remove)
    
    elif call.data == "admin_tickets":
        tickets = db.get_all_tickets('باز')
        if not tickets:
            bot.send_message(call.message.chat.id, "📭 هیچ تیکت باز وجود ندارد.")
            return
        
        text = "📨 **لیست تیکت‌های باز:**\n\n"
        for ticket in tickets:
            ticket_id, user_id, username, t_type, msg, status, date, time = ticket
            text += f"🎫 **تیکت #{ticket_id}**\n"
            text += f"👤 کاربر: {user_id} (@{username})\n"
            text += f"📅 {date} {time}\n"
            text += f"📝 {msg[:100]}...\n"
            text += f"💬 پاسخ: /reply {ticket_id}\n"
            text += "─────────────\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "admin_webhook":
        set_webhook()
        bot.answer_callback_query(call.id, "✅ Webhook ریست شد")

def process_vip_add(message):
    try:
        user_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, "📅 تعداد روزهای VIP را وارد کنید (پیش‌فرض 30):")
        bot.register_next_step_handler(msg, process_vip_days, user_id)
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر است!")

def process_vip_days(message, user_id):
    try:
        days = int(message.text.strip()) if message.text.strip().isdigit() else 30
        db.set_vip(user_id, days, message.from_user.id)
        
        try:
            bot.send_message(user_id, 
                f"💎 **تبریک! شما VIP شدید!**\n\n"
                f"✅ اشتراک {days} روزه فعال شد.\n"
                f"📊 محدودیت شما: {VIP_LIMIT} بار در روز\n"
                f"👨‍💻 سازنده: @{DEVELOPER_USERNAME}")
        except:
            pass
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} با {days} روز VIP شد!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

def process_vip_remove(message):
    try:
        user_id = int(message.text.strip())
        db.remove_vip(user_id)
        
        try:
            bot.send_message(user_id, "❌ اشتراک VIP شما لغو شد.")
        except:
            pass
        
        bot.send_message(message.chat.id, f"✅ VIP کاربر {user_id} حذف شد!")
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر است!")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    if message.chat.id in user_processes:
        user_processes[message.chat.id] = False
        bot.send_message(message.chat.id, "⛔ فرآیند متوقف شد.")
    else:
        bot.send_message(message.chat.id, "⚠️ فرآیندی در حال اجرا نیست.")

@bot.message_handler(commands=['webhook'])
def webhook_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ دسترسی ندارید")
        return
    
    try:
        info = bot.get_webhook_info()
        text = f"📊 **وضعیت Webhook**\n\n"
        text += f"📌 آدرس: {info.url or 'تنظیم نشده'}\n"
        text += f"📊 آپدیت‌ها: {info.pending_update_count}\n"
        if info.last_error_message:
            text += f"⚠️ خطا: {info.last_error_message}\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    bot.reply_to(message, "❌ دستور نامعتبر. از دکمه‌های منو استفاده کنید.")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🤖 ربات SMS Bomber VIP - نسخه نهایی برای رندر")
    print("="*60)
    print(f"👨‍💻 سازنده: @{DEVELOPER_USERNAME}")
    print(f"🤖 بات ارتباطی: @{DEVELOPER_USERNAME}")
    print(f"📢 کانال پشتیبانی: {SUPPORT_CHANNEL}")
    print(f"📌 محدودیت عادی: {NORMAL_LIMIT} بار در روز")
    print(f"📌 محدودیت VIP: {VIP_LIMIT} بار در روز")
    print(f"📌 آدرس API: {LIARA_API_URL}")
    print("="*60)
    
    # تنظیم webhook در ترد جدا
    def run_setup():
        time.sleep(3)
        set_webhook()
    
    threading.Thread(target=run_setup, daemon=True).start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
