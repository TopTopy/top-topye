# -*- coding: utf-8 -*-
"""
🚀 ربات SMS Bomber - نسخه نهایی برای Railway
اتصال به API روی لیارا: https://deathstar-smsbomber-bot.liara.run
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
DEVELOPER_USERNAME = "top_topy_messenger_bot"
DEVELOPER_ID = 8226091292
SUPPORT_CHANNEL = "@death_star_sms_bomber"

# آدرس API روی لیارا - ✅ تنظیم شده
LIARA_API_URL = "https://deathstar-smsbomber-bot.liara.run"
API_TOKEN = "drdragon787_secret_token_2026"

# محدودیت‌های روزانه
NORMAL_LIMIT = 5      # کاربران عادی
VIP_LIMIT = 20        # کاربران VIP
ADMIN_LIMIT = 999999  # ادمین‌ها

# Railway settings
PORT = int(os.environ.get('PORT', 8080))
RAILWAY_URL = os.environ.get('RAILWAY_STATIC_URL', '')
WEBHOOK_URL = f"https://{RAILWAY_URL}/webhook" if RAILWAY_URL else f"https://your-app.up.railway.app/webhook"

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  
]

# ==================== مقداردهی اولیه ====================

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
user_processes = {}
user_sessions = {}  # برای ذخیره وضعیت کاربران

# ==================== دیتابیس درون حافظه ====================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_protected_numbers()
    
    def create_tables(self):
        # جدول کاربران
        self.c.execute('''CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            last_use TEXT,
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
        
        # جدول لاگ استفاده
        self.c.execute('''CREATE TABLE usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
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
    
    def is_phone_protected(self, phone):
        h = hashlib.sha256(phone.encode()).hexdigest()
        self.c.execute("SELECT * FROM blocked_phones WHERE phone_hash = ?", (h,))
        result = self.c.fetchone()
        if result:
            self.c.execute("UPDATE blocked_phones SET attempts = attempts + 1 WHERE phone_hash = ?", (h,))
            self.conn.commit()
            return True
        return False
    
    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()
    
    def register_user(self, user_id, username, first_name, last_name=""):
        today = date.today().isoformat()
        self.c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, join_date, last_use, daily_count, total_count, is_vip)
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
    
    def get_daily_count(self, user_id):
        today = date.today().isoformat()
        self.c.execute("SELECT daily_count, last_use FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        if not result:
            return 0
        count, last = result
        if last != today:
            self.c.execute("UPDATE users SET daily_count = 0, last_use = ? WHERE user_id = ?", (today, user_id))
            self.conn.commit()
            return 0
        return count
    
    def get_user_limit(self, user_id):
        """دریافت محدودیت کاربر بر اساس نوع"""
        if user_id in ADMIN_IDS:
            return ADMIN_LIMIT, "ادمین"
        if self.is_vip(user_id):
            return VIP_LIMIT, "VIP"
        return NORMAL_LIMIT, "عادی"
    
    def increment_usage(self, user_id, phone, success, fail):
        today = date.today().isoformat()
        now = datetime.now().strftime('%H:%M:%S')
        is_vip = 1 if self.is_vip(user_id) else 0
        
        # آپدیت آمار کاربر
        self.c.execute('''UPDATE users SET 
            daily_count = daily_count + 1,
            total_count = total_count + 1,
            last_use = ?
            WHERE user_id = ?''', (today, user_id))
        
        # ثبت لاگ
        self.c.execute('''INSERT INTO usage_logs 
            (user_id, phone, date, time, success_count, fail_count, is_vip)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone, today, now, success, fail, is_vip))
        
        # آپدیت آمار کلی
        self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, total_requests, vip_requests, normal_requests)
            VALUES (?, 
                COALESCE((SELECT total_requests + 1 FROM daily_stats WHERE date = ?), 1),
                COALESCE((SELECT vip_requests + ? FROM daily_stats WHERE date = ?), ?),
                COALESCE((SELECT normal_requests + ? FROM daily_stats WHERE date = ?), ?)
            )''', 
            (today, today, is_vip, today, is_vip, 1 - is_vip, today, 1 - is_vip))
        
        self.conn.commit()
    
    def get_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        total_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        vip_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT SUM(total_requests) FROM daily_stats")
        total_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT SUM(vip_requests) FROM daily_stats")
        vip_requests = self.c.fetchone()[0] or 0
        
        return {
            "total_users": total_users,
            "vip_users": vip_users,
            "total_requests": total_requests,
            "vip_requests": vip_requests,
            "normal_requests": total_requests - vip_requests
        }
    
    def set_vip(self, user_id, days=30):
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

# ایجاد دیتابیس
db = Database()

# ==================== توابع کمکی ====================

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

def check_daily_limit(user_id):
    """بررسی محدودیت روزانه"""
    if is_admin(user_id):
        return True, 0, "ادمین"
    
    daily = db.get_daily_count(user_id)
    limit, user_type = db.get_user_limit(user_id)
    
    return daily < limit, daily, user_type

# ==================== توابع API ====================

def send_to_liara(phone):
    """ارسال درخواست به API لیارا"""
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {"phone": phone}
        
        print(f"📤 ارسال به لیارا: {LIARA_API_URL}/api/bomb")
        
        response = requests.post(
            f"{LIARA_API_URL}/api/bomb",
            json=data,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 پاسخ لیارا: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            return True, result.get("success", 0), result.get("fail", 0), result
        else:
            error_msg = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                error_msg = error_data.get("message", error_msg)
            except:
                pass
            return False, 0, 0, {"error": error_msg}
            
    except requests.exceptions.ConnectionError:
        return False, 0, 0, {"error": "خطا در اتصال به سرور لیارا"}
    except requests.exceptions.Timeout:
        return False, 0, 0, {"error": "تایم اوت در اتصال به لیارا"}
    except Exception as e:
        return False, 0, 0, {"error": str(e)[:100]}

# ==================== صفحات وب ====================

@app.route('/')
def home():
    stats = db.get_stats()
    return f"""
    <html>
        <head>
            <title>🚀 SMS Bomber Bot - Railway</title>
            <style>
                body {{
                    font-family: 'Vazir', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                    padding: 50px;
                    margin: 0;
                }}
                .container {{
                    background: rgba(255,255,255,0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 30px;
                    padding: 40px;
                    max-width: 800px;
                    margin: 0 auto;
                }}
                h1 {{ color: #ffd700; }}
                h2 {{ color: #ffd700; }}
                .stats {{ 
                    display: grid; 
                    grid-template-columns: repeat(3, 1fr); 
                    gap: 20px; 
                    margin: 30px 0;
                }}
                .stat-card {{
                    background: rgba(255,255,255,0.2);
                    border-radius: 15px;
                    padding: 20px;
                }}
                .info {{
                    background: rgba(0,0,0,0.3);
                    border-radius: 15px;
                    padding: 20px;
                    margin-top: 30px;
                }}
                .badge {{
                    background: #4CAF50;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 50px;
                    display: inline-block;
                    margin: 5px;
                }}
                .api-url {{
                    background: rgba(255,215,0,0.2);
                    padding: 15px;
                    border-radius: 10px;
                    font-family: monospace;
                    font-size: 1.2em;
                    margin: 20px 0;
                }}
                a {{ color: #ffd700; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 SMS Bomber Bot</h1>
                <h2>✨ Railway + Liara ✨</h2>
                
                <div class="api-url">
                    🌐 API: {LIARA_API_URL}
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <h3>👥 {stats['total_users']}</h3>
                        <p>کاربران</p>
                    </div>
                    <div class="stat-card">
                        <h3>💎 {stats['vip_users']}</h3>
                        <p>VIP</p>
                    </div>
                    <div class="stat-card">
                        <h3>📊 {stats['total_requests']}</h3>
                        <p>درخواست‌ها</p>
                    </div>
                </div>
                
                <div class="info">
                    <p><span class="badge">✅ بدون پروکسی</span></p>
                    <p><span class="badge">👤 عادی: {NORMAL_LIMIT} بار</span></p>
                    <p><span class="badge">💎 VIP: {VIP_LIMIT} بار</span></p>
                </div>
                
                <p style="margin-top: 30px;">👨‍💻 سازنده: @{DEVELOPER_USERNAME}</p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {
        "status": "healthy",
        "service": "sms-bomber-bot",
        "liara_api": LIARA_API_URL,
        "time": datetime.now().isoformat()
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return 'Error', 500

@app.route('/webhook-status')
def webhook_status():
    try:
        info = bot.get_webhook_info()
        return {
            "url": info.url,
            "pending": info.pending_update_count,
            "last_error": info.last_error_message
        }
    except Exception as e:
        return {"error": str(e)}

# ==================== تنظیم Webhook ====================

def set_webhook():
    try:
        time.sleep(3)
        print(f"📌 تنظیم Webhook...")
        
        if not RAILWAY_URL:
            print("⚠️ RAILWAY_URL مشخص نیست! Webhook را دستی تنظیم کنید.")
            return
        
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=WEBHOOK_URL)
        
        if result:
            print(f"✅ Webhook تنظیم شد: {WEBHOOK_URL}")
            info = bot.get_webhook_info()
            print(f"📊 اطلاعات: {info.url}")
        else:
            print("❌ Webhook تنظیم نشد!")
            
    except Exception as e:
        print(f"❌ خطا: {e}")

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
    
    if is_admin(user_id):
        markup.add(KeyboardButton("👑 پنل مدیریت"))
    
    limit, user_type = db.get_user_limit(user_id)
    
    welcome = (
        "🤖 **به ربات SMS Bomber خوش آمدید!**\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال پشتیبانی:** {SUPPORT_CHANNEL}\n\n"
        f"📌 **محدودیت روزانه:**\n"
        f"• {user_type}: {limit} بار\n\n"
        f"🌐 **API روی لیارا:**\n"
        f"`{LIARA_API_URL}`\n\n"
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

@bot.message_handler(func=lambda m: m.text == "🚀 شروع بمباران")
@membership_required
def ask_phone(message):
    user_id = message.from_user.id
    
    can_use, daily, user_type = check_daily_limit(user_id)
    limit, _ = db.get_user_limit(user_id)
    
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {daily} بار استفاده کرده‌اید.\n"
            f"محدودیت {user_type} {limit} بار است.\n"
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
        bot.send_message(chat_id, "❌ شماره نامعتبر است. باید با 09 شروع شود و 11 رقم باشد.")
        return
    
    if db.is_phone_protected(phone):
        bot.send_message(chat_id, "❌ این شماره در لیست سیاه قرار دارد.")
        return
    
    limit, user_type = db.get_user_limit(user_id)
    remaining = limit - db.get_daily_count(user_id)
    
    bot.send_message(chat_id, f"✅ امروز {remaining} بار دیگر می‌توانید استفاده کنید. (نوع: {user_type})")
    
    user_processes[chat_id] = True
    msg = bot.send_message(chat_id, f"🔰 شروع برای {mask_phone(phone)}...\n🔄 در حال اتصال به سرور لیارا...")
    
    thread = threading.Thread(target=bombing_process, args=(chat_id, user_id, phone, msg.message_id))
    thread.daemon = True
    thread.start()

def bombing_process(chat_id, user_id, phone, msg_id):
    try:
        success, success_count, fail_count, details = send_to_liara(phone)
        
        if success:
            db.increment_usage(user_id, phone, success_count, fail_count)
            
            total = success_count + fail_count
            rate = int(success_count / total * 100) if total > 0 else 0
            user_type = "VIP 💎" if db.is_vip(user_id) else "عادی 👤"
            limit, _ = db.get_user_limit(user_id)
            remaining = limit - db.get_daily_count(user_id)
            
            bot.edit_message_text(
                f"✅ **پایان فرآیند**\n\n"
                f"📱 **شماره:** {mask_phone(phone)}\n"
                f"👤 **نوع کاربر:** {user_type}\n"
                f"✅ **موفق:** {success_count}\n"
                f"❌ **ناموفق:** {fail_count}\n"
                f"📊 **نرخ موفقیت:** {rate}%\n"
                f"🔰 **باقیمانده امروز:** {remaining}\n"
                f"🌐 **سرور:** لیارا\n"
                f"🔗 `{LIARA_API_URL}`",
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
    user_id = message.from_user.id
    limit, user_type = db.get_user_limit(user_id)
    
    text = (
        "📚 **راهنمای استفاده**\n\n"
        "1️⃣ روی دکمه **🚀 شروع بمباران** کلیک کنید\n"
        "2️⃣ شماره موبایل را وارد کنید\n"
        "3️⃣ منتظر بمانید\n\n"
        f"👤 **نوع کاربر:** {user_type}\n"
        f"📊 **محدودیت:** {limit} بار در روز\n"
        f"🔰 **تعداد APIها:** 100+ (روی لیارا)\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال پشتیبانی:** {SUPPORT_CHANNEL}\n\n"
        f"🌐 **آدرس API:**\n`{LIARA_API_URL}`\n\n"
        "💎 **برای دریافت VIP با ادمین تماس بگیرید**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def my_stats(message):
    user_id = message.from_user.id
    daily = db.get_daily_count(user_id)
    limit, user_type = db.get_user_limit(user_id)
    remaining = limit - daily
    
    stats = db.get_stats()
    
    text = (
        f"📊 **آمار شما**\n\n"
        f"🆔 **آیدی:** `{user_id}`\n"
        f"👤 **نوع:** {user_type}\n"
        f"📊 **امروز:** {daily}/{limit}\n"
        f"✅ **باقیمانده:** {remaining}\n"
        f"🔰 **کل کاربران:** {stats['total_users']}\n"
        f"💎 **VIP:** {stats['vip_users']}"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💎 وضعیت VIP")
def vip_status(message):
    user_id = message.from_user.id
    
    if db.is_vip(user_id):
        daily = db.get_daily_count(user_id)
        remaining = VIP_LIMIT - daily
        
        text = (
            "💎 **وضعیت VIP شما**\n\n"
            "✅ شما کاربر ویژه هستید\n"
            f"📊 محدودیت شما: {VIP_LIMIT} بار در روز\n"
            f"📊 استفاده امروز: {daily}/{VIP_LIMIT}\n"
            f"✅ باقیمانده: {remaining}\n\n"
            "🔰 مزایا: محدودیت بالاتر"
        )
    else:
        text = (
            "💎 **دریافت VIP**\n\n"
            "با دریافت VIP می‌توانید:\n"
            f"• روزانه {VIP_LIMIT} بار استفاده کنید\n"
            "• پشتیبانی優先\n\n"
            f"برای دریافت با ادمین تماس بگیرید: @{DEVELOPER_USERNAME}"
        )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support_handler(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👨‍💻 تماس با سازنده", url=f"https://t.me/{DEVELOPER_USERNAME}"),
        InlineKeyboardButton("📢 کانال", url=CHANNEL_LINK)
    )
    
    text = (
        "📞 **پشتیبانی**\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال:** {SUPPORT_CHANNEL}\n\n"
        "برای ارتباط مستقیم با سازنده، از دکمه زیر استفاده کنید:"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ دسترسی غیرمجاز!")
        return
    
    stats = db.get_stats()
    vips = db.get_vip_list()
    
    text = (
        "👑 **پنل مدیریت**\n\n"
        f"📊 **آمار کلی:**\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"💎 VIP: {stats['vip_users']}\n"
        f"📊 کل درخواست: {stats['total_requests']}\n"
        f"💎 درخواست VIP: {stats['vip_requests']}\n"
        f"👤 درخواست عادی: {stats['normal_requests']}\n\n"
        f"🌐 **وضعیت لیارا:**\n"
        f"• آدرس: {LIARA_API_URL}\n"
        f"• وضعیت: {'🟢 فعال' if LIARA_API_URL else '🔴 غیرفعال'}\n\n"
        f"💎 **VIP‌ها:** {len(vips)} نفر"
    )
    
    # دکمه‌های مدیریتی
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list"),
        InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add"),
        InlineKeyboardButton("🔄 ریست Webhook", callback_data="reset_webhook")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["vip_list", "vip_add", "reset_webhook"])
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی ندارید!")
        return
    
    if call.data == "vip_list":
        vips = db.get_vip_list()
        if vips:
            text = "📋 **لیست VIPها:**\n\n"
            for vip in vips:
                user_id, username, name, expiry = vip
                expiry_date = expiry.split('T')[0] if expiry else "نامشخص"
                text += f"• {name} - `{user_id}`\n  ⏳ {expiry_date}\n"
        else:
            text = "📭 هیچ کاربر VIP وجود ندارد"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "vip_add":
        msg = bot.send_message(call.message.chat.id, 
            "➕ **افزودن VIP**\n\n"
            "آیدی عددی کاربر را وارد کنید:")
        bot.register_next_step_handler(msg, process_vip_add)
    
    elif call.data == "reset_webhook":
        set_webhook()
        bot.answer_callback_query(call.id, "✅ Webhook ریست شد")

def process_vip_add(message):
    try:
        user_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, "📅 تعداد روزها (پیش‌فرض 30):")
        bot.register_next_step_handler(msg, process_vip_days, user_id)
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر!")

def process_vip_days(message, user_id):
    try:
        days = int(message.text.strip()) if message.text.strip().isdigit() else 30
        db.set_vip(user_id, days)
        
        try:
            bot.send_message(user_id, 
                f"💎 **تبریک! شما VIP شدید!**\n\n"
                f"✅ اشتراک {days} روزه فعال شد.\n"
                f"📊 محدودیت شما: {VIP_LIMIT} بار در روز")
        except:
            pass
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} VIP شد!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    if message.chat.id in user_processes:
        user_processes[message.chat.id] = False
        bot.send_message(message.chat.id, "⛔ فرآیند متوقف شد.")
    else:
        bot.send_message(message.chat.id, "⚠️ فرآیندی در حال اجرا نیست.")

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    bot.reply_to(
        message, 
        "❌ دستور نامعتبر!\nاز دکمه‌های منوی ربات استفاده کنید."
    )

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🚀 ربات SMS Bomber - نسخه Railway + Liara")
    print("="*60)
    print(f"👨‍💻 سازنده: @{DEVELOPER_USERNAME}")
    print(f"📢 کانال: {SUPPORT_CHANNEL}")
    print(f"📌 آدرس API: {LIARA_API_URL}")
    print(f"📌 API Token: {API_TOKEN[:20]}...")
    print("="*60)
    
    # تنظیم webhook
    threading.Thread(target=set_webhook, daemon=True).start()
    
    # اجرا
    port = PORT
    print(f"🚀 اجرا روی پورت {port}")
    app.run(host='0.0.0.0', port=port)
