# -*- coding: utf-8 -*-
"""
🚀 ربات SMS + Call Bomber - نسخه نهایی با رفع خطای اتصال به لیارا
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

BOT_TOKEN = "8098018364:"
SUPER_ADMINS = [7620484201, 8226091292]  # ادمین‌های اصلی

# ==================== تنظیمات عضویت اجباری ====================

REQUIRED_CHANNEL = -1003826727202   # آیدی عددی کانال
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"  # لینک کانال

# آدرس API روی لیارا
LIARA_API_URL = "https://deathstar-smsbomber-bot.liara.run"
API_TOKEN = "drdragon787_secret_token_2026"

# محدودیت‌های روزانه
NORMAL_SMS_LIMIT = 5      # کاربران عادی - SMS
NORMAL_CALL_LIMIT = 0      # کاربران عادی - CALL (0 یعنی دسترسی ندارند)
VIP_SMS_LIMIT = 20         # کاربران VIP - SMS
VIP_CALL_LIMIT = 10        # کاربران VIP - CALL
VIP_COMBO_LIMIT = 5        # کاربران VIP - ترکیبی (SMS + CALL همزمان)

# Railway settings
PORT = int(os.environ.get('PORT', 8080))
RAILWAY_URL = os.environ.get('RAILWAY_STATIC_URL', 'web-production-71444.up.railway.app')
WEBHOOK_URL = f"https://{RAILWAY_URL}/webhook"

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  #
]

# وضعیت بات
BOT_ACTIVE = True

# ==================== مقداردهی اولیه ====================

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
user_processes = {}
user_sessions = {}

# ==================== بررسی عضویت ====================

def check_membership(user_id):
    """بررسی عضویت کاربر در کانال"""
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        
        # اگر کاربر لفت یا بن شده باشه
        if member.status in ['left', 'kicked']:
            return False
        
        return True

    except Exception as e:
        print(f"⚠️ Membership check error: {e}")
        return False


# ==================== دکوراتور عضویت اجباری ====================

def membership_required(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id

        # اگر ربات خاموشه و کاربر ادمین نیست
        if not db.get_bot_status() and not is_admin(user_id):
            bot.reply_to(message, "⚠️ ربات در حال حاضر غیرفعال است.")
            return

        # ادمین‌ها معاف
        if is_admin(user_id):
            return func(message, *args, **kwargs)

        # بررسی عضویت
        if check_membership(user_id):
            return func(message, *args, **kwargs)
        else:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)
            )
            markup.add(
                InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")
            )

            bot.reply_to(
                message,
                "⚠️ برای استفاده از ربات باید ابتدا در کانال عضو شوید.",
                reply_markup=markup
            )

    return wrapper

# ==================== هندلر دکمه بررسی عضویت ====================

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id if call.message else None
    message_id = call.message.message_id if call.message else None

    if check_membership(user_id):

        # پاسخ به دکمه
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد")

        # حذف پیام اگر وجود داشت
        if chat_id and message_id:
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass

        # ارسال پیام موفقیت
        if chat_id:
            bot.send_message(chat_id, "🎉 عضویت شما تایید شد!\nالان می‌تونی از ربات استفاده کنی.")

    else:
        bot.answer_callback_query(
            call.id,
            "❌ هنوز در کانال عضو نشده‌اید!",
            show_alert=True
        )

# ==================== دیتابیس درون حافظه ====================

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.c = self.conn.cursor()
        self.create_tables()
        self.add_protected_numbers()
        self.add_super_admins()
    
    def create_tables(self):
        self.c.execute('''CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            last_use_sms TEXT,
            last_use_call TEXT,
            last_use_combo TEXT,
            daily_sms_count INTEGER DEFAULT 0,
            daily_call_count INTEGER DEFAULT 0,
            daily_combo_count INTEGER DEFAULT 0,
            total_sms_count INTEGER DEFAULT 0,
            total_call_count INTEGER DEFAULT 0,
            total_combo_count INTEGER DEFAULT 0,
            is_vip INTEGER DEFAULT 0,
            vip_expiry TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT
        )''')
        
        self.c.execute('''CREATE TABLE blocked_phones (
            phone_hash TEXT PRIMARY KEY,
            date TEXT,
            reason TEXT,
            attempts INTEGER DEFAULT 0
        )''')
        
        self.c.execute('''CREATE TABLE daily_stats (
            date TEXT PRIMARY KEY,
            sms_requests INTEGER DEFAULT 0,
            call_requests INTEGER DEFAULT 0,
            combo_requests INTEGER DEFAULT 0
        )''')
        
        self.c.execute('''CREATE TABLE usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
            type TEXT,
            date TEXT,
            time TEXT,
            success_count INTEGER,
            fail_count INTEGER,
            is_vip INTEGER
        )''')
        
        self.c.execute('''CREATE TABLE bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        self.c.execute("INSERT OR IGNORE INTO bot_settings VALUES (?, ?)", ("bot_active", "true"))
        
        self.conn.commit()
    
    def add_protected_numbers(self):
        today = datetime.now().strftime('%Y-%m-%d')
        for h in PROTECTED_PHONE_HASHES:
            self.c.execute("INSERT OR IGNORE INTO blocked_phones VALUES (?, ?, ?, ?)", 
                          (h, today, "شماره محافظت شده", 0))
        self.conn.commit()
    
    def add_super_admins(self):
        today = date.today().isoformat()
        for admin_id in SUPER_ADMINS:
            self.c.execute('''INSERT OR IGNORE INTO users 
                (user_id, username, first_name, join_date, last_use_sms, last_use_call, last_use_combo, 
                 daily_sms_count, daily_call_count, daily_combo_count, total_sms_count, total_call_count, total_combo_count, is_admin)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 1)''',
                (admin_id, "super_admin", "ادمین", today, today, today, today))
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
    
    def register_user(self, user_id, username, first_name, last_name=""):
        today = date.today().isoformat()
        self.c.execute('''INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, join_date, last_use_sms, last_use_call, last_use_combo,
             daily_sms_count, daily_call_count, daily_combo_count, total_sms_count, total_call_count, total_combo_count, is_vip, is_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0)''',
            (user_id, username, first_name, last_name, today, today, today, today))
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
    
    def is_admin(self, user_id):
        if user_id in SUPER_ADMINS:
            return True
        self.c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        return result and result[0] == 1
    
    def make_admin(self, user_id):
        self.c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return True
    
    def get_daily_counts(self, user_id):
        """دریافت آمار روزانه کاربر"""
        today = date.today().isoformat()
        self.c.execute('''SELECT daily_sms_count, daily_call_count, daily_combo_count, 
                                last_use_sms, last_use_call, last_use_combo 
                         FROM users WHERE user_id = ?''', (user_id,))
        result = self.c.fetchone()
        if not result:
            return 0, 0, 0
        
        sms_count, call_count, combo_count, last_sms, last_call, last_combo = result
        
        if last_sms != today:
            sms_count = 0
            self.c.execute("UPDATE users SET daily_sms_count = 0, last_use_sms = ? WHERE user_id = ?", (today, user_id))
        
        if last_call != today:
            call_count = 0
            self.c.execute("UPDATE users SET daily_call_count = 0, last_use_call = ? WHERE user_id = ?", (today, user_id))
        
        if last_combo != today:
            combo_count = 0
            self.c.execute("UPDATE users SET daily_combo_count = 0, last_use_combo = ? WHERE user_id = ?", (today, user_id))
        
        self.conn.commit()
        return sms_count, call_count, combo_count
    
    def get_user_limits(self, user_id):
        """دریافت محدودیت‌های کاربر"""
        if self.is_admin(user_id):
            return 999999, 999999, 999999, "ادمین"
        
        if self.is_vip(user_id):
            return VIP_SMS_LIMIT, VIP_CALL_LIMIT, VIP_COMBO_LIMIT, "VIP 💎"
        
        return NORMAL_SMS_LIMIT, NORMAL_CALL_LIMIT, 0, "عادی 👤"  # کامبو و کال فقط برای VIP
    
    def can_use_call(self, user_id):
        """بررسی دسترسی به تماس"""
        if self.is_admin(user_id):
            return True
        return self.is_vip(user_id)
    
    def can_use_combo(self, user_id):
        """بررسی دسترسی به ترکیبی"""
        if self.is_admin(user_id):
            return True
        return self.is_vip(user_id)
    
    def increment_usage(self, user_id, phone, bomb_type, success, fail):
        """افزایش آمار استفاده"""
        today = date.today().isoformat()
        now = datetime.now().strftime('%H:%M:%S')
        is_vip = 1 if self.is_vip(user_id) else 0
        
        if bomb_type == "sms":
            self.c.execute('''UPDATE users SET 
                daily_sms_count = daily_sms_count + 1,
                total_sms_count = total_sms_count + 1,
                last_use_sms = ?
                WHERE user_id = ?''', (today, user_id))
            
            self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, sms_requests, call_requests, combo_requests)
                VALUES (?, 
                    COALESCE((SELECT sms_requests + 1 FROM daily_stats WHERE date = ?), 1),
                    COALESCE((SELECT call_requests FROM daily_stats WHERE date = ?), 0),
                    COALESCE((SELECT combo_requests FROM daily_stats WHERE date = ?), 0)
                )''', (today, today, today, today))
            
        elif bomb_type == "call":
            self.c.execute('''UPDATE users SET 
                daily_call_count = daily_call_count + 1,
                total_call_count = total_call_count + 1,
                last_use_call = ?
                WHERE user_id = ?''', (today, user_id))
            
            self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, sms_requests, call_requests, combo_requests)
                VALUES (?, 
                    COALESCE((SELECT sms_requests FROM daily_stats WHERE date = ?), 0),
                    COALESCE((SELECT call_requests + 1 FROM daily_stats WHERE date = ?), 1),
                    COALESCE((SELECT combo_requests FROM daily_stats WHERE date = ?), 0)
                )''', (today, today, today, today))
            
        elif bomb_type == "combo":
            self.c.execute('''UPDATE users SET 
                daily_combo_count = daily_combo_count + 1,
                total_combo_count = total_combo_count + 1,
                last_use_combo = ?
                WHERE user_id = ?''', (today, user_id))
            
            self.c.execute('''INSERT OR REPLACE INTO daily_stats (date, sms_requests, call_requests, combo_requests)
                VALUES (?, 
                    COALESCE((SELECT sms_requests FROM daily_stats WHERE date = ?), 0),
                    COALESCE((SELECT call_requests FROM daily_stats WHERE date = ?), 0),
                    COALESCE((SELECT combo_requests + 1 FROM daily_stats WHERE date = ?), 1)
                )''', (today, today, today, today))
        
        # ثبت لاگ
        self.c.execute('''INSERT INTO usage_logs 
            (user_id, phone, type, date, time, success_count, fail_count, is_vip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, phone, bomb_type, today, now, success, fail, is_vip))
        
        self.conn.commit()
    
    def get_stats(self):
        self.c.execute("SELECT COUNT(*) FROM users")
        total_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        vip_users = self.c.fetchone()[0]
        
        self.c.execute("SELECT SUM(sms_requests) FROM daily_stats")
        sms_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT SUM(call_requests) FROM daily_stats")
        call_requests = self.c.fetchone()[0] or 0
        
        self.c.execute("SELECT SUM(combo_requests) FROM daily_stats")
        combo_requests = self.c.fetchone()[0] or 0
        
        admins = self.get_admins()
        
        return {
            "total_users": total_users,
            "vip_users": vip_users,
            "admin_users": len(admins),
            "sms_requests": sms_requests,
            "call_requests": call_requests,
            "combo_requests": combo_requests,
            "total_requests": sms_requests + call_requests + combo_requests
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
    
    def get_admins(self):
        self.c.execute("SELECT user_id, username, first_name FROM users WHERE is_admin = 1")
        admins = self.c.fetchall()
        for admin_id in SUPER_ADMINS:
            if admin_id not in [a[0] for a in admins]:
                admins.append((admin_id, "super_admin", "سوپر ادمین"))
        return admins
    
    def get_bot_status(self):
        self.c.execute("SELECT value FROM bot_settings WHERE key = 'bot_active'")
        result = self.c.fetchone()
        return result and result[0] == "true"
    
    def set_bot_status(self, status):
        self.c.execute("UPDATE bot_settings SET value = ? WHERE key = 'bot_active'", 
                      ("true" if status else "false"))
        self.conn.commit()
        return True

# ایجاد دیتابیس
db = Database()

# ==================== توابع کمکی ====================

def mask_phone(phone):
    return phone[:4] + "****" + phone[-4:]

def is_admin(user_id):
    return db.is_admin(user_id)

def is_super_admin(user_id):
    return user_id in SUPER_ADMINS

def vip_or_admin_required(func):
    """دکوراتور برای دسترسی VIP یا ادمین"""
    def wrapper(message):
        user_id = message.from_user.id
        if is_admin(user_id) or db.is_vip(user_id):
            return func(message)
        else:
            bot.reply_to(message, "💎 این بخش فقط برای کاربران VIP قابل دسترسی است!\nبرای دریافت VIP با ادمین تماس بگیرید.")
            return
    return wrapper

def admin_only(func):
    def wrapper(message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "⛔ این بخش فقط برای ادمین‌ها قابل دسترسی است!")
            return
        return func(message)
    return wrapper

def check_daily_limit(user_id, bomb_type):
    """بررسی محدودیت روزانه"""
    if is_admin(user_id):
        return True, 0
    
    sms_count, call_count, combo_count = db.get_daily_counts(user_id)
    sms_limit, call_limit, combo_limit, _ = db.get_user_limits(user_id)
    
    if bomb_type == "sms":
        return sms_count < sms_limit, sms_count
    elif bomb_type == "call":
        # کاربران عادی به تماس دسترسی ندارند
        if not db.can_use_call(user_id):
            return False, 0
        return call_count < call_limit, call_count
    elif bomb_type == "combo":
        # فقط VIP به ترکیبی دسترسی دارند
        if not db.can_use_combo(user_id):
            return False, 0
        return combo_count < combo_limit, combo_count
    
    return False, 0

# ==================== توابع بررسی اتصال به لیارا ====================

def check_liara_connection():
    """بررسی اتصال به لیارا"""
    try:
        print(f"🔄 Checking Liara connection: {LIARA_API_URL}/health")
        response = requests.get(
            f"{LIARA_API_URL}/health",
            timeout=5
        )
        print(f"✅ Liara response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

# ==================== توابع ارسال به لیارا ====================

def send_to_liara(phone, bomb_type="sms"):
    """ارسال درخواست به API لیارا"""
    try:
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "phone": phone,
            "type": bomb_type
        }
        
        print(f"📤 Sending to Liara: {bomb_type} - {phone}")
        response = requests.post(
            f"{LIARA_API_URL}/api/bomb",
            json=data,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 Response: {response.status_code}")
        
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
            
    except requests.exceptions.Timeout:
        print("❌ Timeout error")
        return False, 0, 0, {"error": "تایم اوت در اتصال به لیارا"}
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, 0, 0, {"error": str(e)[:100]}

# ==================== صفحات وب ====================

@app.route('/')
def home():
    stats = db.get_stats()
    return f"""
    <html>
        <head>
            <title>🚀 SMS + Call + Combo Bomber Bot</title>
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
                .call-badge {{
                    background: #f44336;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 50px;
                    display: inline-block;
                    margin: 5px;
                }}
                .vip-badge {{
                    background: #ffd700;
                    color: black;
                    padding: 5px 15px;
                    border-radius: 50px;
                    display: inline-block;
                    margin: 5px;
                    font-weight: bold;
                }}
                .limits {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 SMS + Call + Combo Bomber</h1>
                <p>✨ Railway + Liara ✨</p>
                
                <div class="limits">
                    <span class="badge">📱 SMS: {NORMAL_SMS_LIMIT}</span>
                    <span class="call-badge">📞 CALL: فقط VIP</span>
                    <span class="vip-badge">💎 COMBO: فقط VIP</span>
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
                    <p>👨‍💻 سازنده: @top_topy_messenger_bot</p>
                    <p>📢 کانال پشتیبانی: @death_star_sms_bomber</p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    stats = db.get_stats()
    return {
        "status": "healthy",
        "bot_status": "active" if db.get_bot_status() else "inactive",
        "total_users": stats['total_users'],
        "vip_users": stats['vip_users'],
        "total_requests": stats['total_requests'],
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
        return 'Error', 500

# ==================== تنظیم Webhook و جلوگیری از خواب ====================

def keep_alive():
    """ترد جدا برای جلوگیری از خواب ربات"""
    while True:
        try:
            time.sleep(600)
            print(f"💓 پینگ زنده نگه داشتن - {datetime.now().strftime('%H:%M:%S')}")
            requests.get(f"https://{RAILWAY_URL}/health", timeout=5)
        except:
            pass

def set_webhook():
    try:
        time.sleep(3)
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=WEBHOOK_URL)
        if result:
            print(f"✅ Webhook تنظیم شد: {WEBHOOK_URL}")
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
    
    # دکمه SMS برای همه
    markup.add(KeyboardButton("📱 بمباران SMS"))
    
    # دکمه تماس و ترکیبی فقط برای VIP یا ادمین
    if db.can_use_call(user_id) or is_admin(user_id):
        markup.add(KeyboardButton("📞 بمباران تماس (VIP)"))
    
    if db.can_use_combo(user_id) or is_admin(user_id):
        markup.add(KeyboardButton("💎 بمباران ترکیبی (VIP)"))
    
    # دکمه‌های عمومی
    markup.add(KeyboardButton("📊 راهنما"), KeyboardButton("📊 آمار من"))
    markup.add(KeyboardButton("📞 پشتیبانی"), KeyboardButton("💎 وضعیت VIP"))
    
    if is_admin(user_id):
        markup.add(KeyboardButton("👑 پنل مدیریت"))
    
    sms_count, call_count, combo_count = db.get_daily_counts(user_id)
    sms_limit, call_limit, combo_limit, user_type = db.get_user_limits(user_id)
    
    # ✅ پیام خوش‌آمدگویی
    welcome = (
        "🤖 **به ربات SMS Bomber خوش آمدید!**\n\n"
        "👨‍💻 **سازنده:** @top_topy_messenger_bot\n"
        "📢 **کانال پشتیبانی:** @death_star_sms_bomber\n\n"
        f"👤 **نوع کاربر:** {user_type}\n\n"
        f"📱 **SMS امروز:** {sms_count}/{sms_limit}\n"
    )
    
    if db.can_use_call(user_id):
        welcome += f"📞 **تماس امروز:** {call_count}/{call_limit}\n"
    else:
        welcome += f"📞 **تماس:** ❌ فقط برای VIP\n"
    
    if db.can_use_combo(user_id):
        welcome += f"💎 **ترکیبی امروز:** {combo_count}/{combo_limit}\n"
    else:
        welcome += f"💎 **ترکیبی:** ❌ فقط برای VIP\n"
    
    welcome += "\n🚀 برای شروع از دکمه‌های زیر استفاده کنید:"
    
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📱 بمباران SMS")
@membership_required
def ask_phone_sms(message):
    user_id = message.from_user.id
    
    if not db.get_bot_status() and not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ ربات در حال حاضر غیرفعال است.")
        return
    
    can_use, current = check_daily_limit(user_id, "sms")
    limit, _, _, _ = db.get_user_limits(user_id)
    
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {current} بار SMS استفاده کرده‌اید.\n"
            f"محدودیت شما {limit} بار است.\n"
            "فردا دوباره تلاش کنید."
        )
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست.")
        return
    
    user_sessions[user_id] = {"type": "sms"}
    msg = bot.send_message(message.chat.id, "📱 شماره موبایل را برای بمباران SMS وارد کنید (مثال: 09123456789):")
    bot.register_next_step_handler(msg, process_phone)

@bot.message_handler(func=lambda m: m.text == "📞 بمباران تماس (VIP)")
@membership_required
@vip_or_admin_required
def ask_phone_call(message):
    user_id = message.from_user.id
    
    if not db.get_bot_status() and not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ ربات در حال حاضر غیرفعال است.")
        return
    
    can_use, current = check_daily_limit(user_id, "call")
    _, limit, _, _ = db.get_user_limits(user_id)
    
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {current} بار تماس استفاده کرده‌اید.\n"
            f"محدودیت شما {limit} بار است.\n"
            "فردا دوباره تلاش کنید."
        )
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست.")
        return
    
    user_sessions[user_id] = {"type": "call"}
    msg = bot.send_message(message.chat.id, "📞 شماره موبایل را برای بمباران تماس وارد کنید (مثال: 09123456789):")
    bot.register_next_step_handler(msg, process_phone)

@bot.message_handler(func=lambda m: m.text == "💎 بمباران ترکیبی (VIP)")
@membership_required
@vip_or_admin_required
def ask_phone_combo(message):
    user_id = message.from_user.id
    
    if not db.get_bot_status() and not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ ربات در حال حاضر غیرفعال است.")
        return
    
    can_use, current = check_daily_limit(user_id, "combo")
    _, _, limit, _ = db.get_user_limits(user_id)
    
    if not can_use:
        bot.send_message(
            message.chat.id, 
            f"❌ شما امروز {current} بار ترکیبی استفاده کرده‌اید.\n"
            f"محدودیت شما {limit} بار است.\n"
            "فردا دوباره تلاش کنید."
        )
        return
    
    if user_processes.get(message.chat.id):
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست.")
        return
    
    user_sessions[user_id] = {"type": "combo"}
    msg = bot.send_message(message.chat.id, "💎 شماره موبایل را برای بمباران ترکیبی (SMS + تماس همزمان) وارد کنید (مثال: 09123456789):")
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
    
    bomb_type = user_sessions.get(user_id, {}).get("type", "sms")
    sms_limit, call_limit, combo_limit, user_type = db.get_user_limits(user_id)
    
    sms_count, call_count, combo_count = db.get_daily_counts(user_id)
    
    if bomb_type == "sms":
        remaining = sms_limit - sms_count
    elif bomb_type == "call":
        remaining = call_limit - call_count
    else:
        remaining = combo_limit - combo_count
    
    bot.send_message(chat_id, f"✅ امروز {remaining} بار دیگر می‌توانید استفاده کنید. (نوع: {bomb_type})")
    
    user_processes[chat_id] = True
    
    if bomb_type == "sms":
        msg = bot.send_message(chat_id, f"📱 شروع بمباران SMS برای {mask_phone(phone)}...\n🔄 در حال ارسال...")
    elif bomb_type == "call":
        msg = bot.send_message(chat_id, f"📞 شروع بمباران تماس برای {mask_phone(phone)}...\n🔄 در حال ارسال...")
    else:
        msg = bot.send_message(chat_id, f"💎 شروع بمباران ترکیبی برای {mask_phone(phone)}...\n🔄 در حال ارسال...")
    
    thread = threading.Thread(target=bombing_process, args=(chat_id, user_id, phone, bomb_type, msg.message_id))
    thread.daemon = True
    thread.start()

def bombing_process(chat_id, user_id, phone, bomb_type, msg_id):
    """فرآیند بمباران با بررسی اتصال اولیه"""
    try:
        # اول اتصال رو چک کن
        if not check_liara_connection():
            bot.edit_message_text(
                f"❌ **خطا در اتصال به سرور لیارا**\n\n"
                f"📱 **شماره:** {mask_phone(phone)}\n"
                f"⚠️ **خطا:** سرور لیارا در دسترس نیست\n\n"
                f"🔄 لطفاً چند دقیقه بعد تلاش کنید.",
                chat_id, msg_id,
                parse_mode="Markdown"
            )
            return
        
        success, success_count, fail_count, details = send_to_liara(phone, bomb_type)
        
        if success:
            db.increment_usage(user_id, phone, bomb_type, success_count, fail_count)
            
            total = success_count + fail_count
            rate = int(success_count / total * 100) if total > 0 else 0
            
            sms_count, call_count, combo_count = db.get_daily_counts(user_id)
            sms_limit, call_limit, combo_limit, user_type = db.get_user_limits(user_id)
            
            if bomb_type == "sms":
                remaining = sms_limit - sms_count
                emoji = "📱"
                type_text = "SMS"
            elif bomb_type == "call":
                remaining = call_limit - call_count
                emoji = "📞"
                type_text = "تماس"
            else:
                remaining = combo_limit - combo_count
                emoji = "💎"
                type_text = "ترکیبی"
            
            bot.edit_message_text(
                f"✅ **پایان بمباران {type_text}**\n\n"
                f"{emoji} **شماره:** {mask_phone(phone)}\n"
                f"👤 **نوع کاربر:** {user_type}\n"
                f"✅ **موفق:** {success_count}\n"
                f"❌ **ناموفق:** {fail_count}\n"
                f"📊 **نرخ موفقیت:** {rate}%\n"
                f"🔰 **باقیمانده امروز:** {remaining}",
                chat_id, msg_id,
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                f"❌ **خطا در اتصال به سرور**\n\n"
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
@membership_required
def help_message(message):
    user_id = message.from_user.id
    sms_limit, call_limit, combo_limit, user_type = db.get_user_limits(user_id)
    
    text = (
        "📚 **راهنمای استفاده**\n\n"
        "**🔹 بمباران SMS** 📱\n"
        "• برای همه کاربران\n"
        f"• محدودیت {user_type}: {sms_limit} بار در روز\n\n"
    )
    
    if db.can_use_call(user_id):
        text += (
            "**📞 بمباران تماس**\n"
            "• مخصوص کاربران VIP\n"
            f"• محدودیت VIP: {call_limit} بار در روز\n\n"
        )
    else:
        text += (
            "**📞 بمباران تماس**\n"
            "• فقط برای کاربران VIP\n"
            "• برای دریافت VIP با ادمین تماس بگیرید\n\n"
        )
    
    if db.can_use_combo(user_id):
        text += (
            "**💎 بمباران ترکیبی (VIP)**\n"
            "• مخصوص کاربران VIP\n"
            "• ارسال همزمان SMS و تماس\n"
            f"• محدودیت VIP: {combo_limit} بار در روز\n\n"
        )
    else:
        text += (
            "**💎 بمباران ترکیبی**\n"
            "• فقط برای کاربران VIP\n"
            "• ارسال همزمان SMS و تماس\n\n"
        )
    
    text += (
        "👨‍💻 **سازنده:** @top_topy_messenger_bot\n"
        "📢 **کانال پشتیبانی:** @death_star_sms_bomber"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
@membership_required
def my_stats(message):
    user_id = message.from_user.id
    sms_count, call_count, combo_count = db.get_daily_counts(user_id)
    sms_limit, call_limit, combo_limit, user_type = db.get_user_limits(user_id)
    
    stats = db.get_stats()
    
    text = (
        f"📊 **آمار شما**\n\n"
        f"🆔 **آیدی:** `{user_id}`\n"
        f"👤 **نوع:** {user_type}\n\n"
        f"📱 **SMS امروز:** {sms_count}/{sms_limit}\n"
    )
    
    if db.can_use_call(user_id):
        text += f"📞 **تماس امروز:** {call_count}/{call_limit}\n"
    
    if db.can_use_combo(user_id):
        text += f"💎 **ترکیبی امروز:** {combo_count}/{combo_limit}\n\n"
    else:
        text += "\n"
    
    text += (
        f"👥 **کل کاربران:** {stats['total_users']}\n"
        f"💎 **VIP:** {stats['vip_users']}"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💎 وضعیت VIP")
@membership_required
def vip_status(message):
    user_id = message.from_user.id
    
    if db.is_vip(user_id):
        sms_count, call_count, combo_count = db.get_daily_counts(user_id)
        remaining_call = VIP_CALL_LIMIT - call_count
        remaining_combo = VIP_COMBO_LIMIT - combo_count
        
        text = (
            "💎 **وضعیت VIP شما**\n\n"
            "✅ شما کاربر ویژه هستید\n"
            f"📊 محدودیت SMS: {VIP_SMS_LIMIT} بار\n"
            f"📊 محدودیت تماس: {VIP_CALL_LIMIT} بار\n"
            f"📊 محدودیت ترکیبی: {VIP_COMBO_LIMIT} بار\n\n"
            f"📞 استفاده تماس امروز: {call_count}/{VIP_CALL_LIMIT}\n"
            f"✅ باقیمانده تماس: {remaining_call}\n"
            f"💎 استفاده ترکیبی امروز: {combo_count}/{VIP_COMBO_LIMIT}\n"
            f"✅ باقیمانده ترکیبی: {remaining_combo}\n\n"
            "🔰 مزایا: دسترسی به تماس و بمباران ترکیبی"
        )
    else:
        text = (
            "💎 **دریافت VIP**\n\n"
            "با دریافت VIP می‌توانید:\n"
            f"• روزانه {VIP_SMS_LIMIT} بار SMS\n"
            f"• روزانه {VIP_CALL_LIMIT} بار تماس\n"
            f"• 💥 {VIP_COMBO_LIMIT} بار بمباران ترکیبی (SMS + تماس همزمان)\n"
            "• پشتیبانی優先\n\n"
            f"برای دریافت با ادمین تماس بگیرید: @top_topy_messenger_bot"
        )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 پشتیبانی")
def support_handler(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👨‍💻 تماس با سازنده", url="https://t.me/top_topy_messenger_bot"),
        InlineKeyboardButton("📢 کانال", url=CHANNEL_LINK)
    )
    
    text = (
        "📞 **پشتیبانی**\n\n"
        "👨‍💻 **سازنده:** @top_topy_messenger_bot\n"
        "📢 **کانال:** @death_star_sms_bomber\n\n"
        "برای ارتباط مستقیم با سازنده، از دکمه زیر استفاده کنید:"
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ==================== پنل مدیریت (فقط ادمین) ====================

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
@admin_only
def admin_panel(message):
    stats = db.get_stats()
    bot_status = db.get_bot_status()
    vips = db.get_vip_list()
    
    text = (
        "👑 **پنل مدیریت**\n\n"
        f"📊 **آمار کلی:**\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"👑 ادمین‌ها: {stats['admin_users']}\n"
        f"💎 VIP: {stats['vip_users']}\n\n"
        f"📱 SMS درخواست: {stats['sms_requests']}\n"
        f"📞 تماس درخواست: {stats['call_requests']}\n"
        f"💎 ترکیبی درخواست: {stats['combo_requests']}\n\n"
        f"⚡ **وضعیت بات:** {'🟢 روشن' if bot_status else '🔴 خاموش'}"
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📋 لیست VIP", callback_data="admin_vip_list"),
        InlineKeyboardButton("➕ افزودن VIP", callback_data="admin_vip_add")
    )
    
    markup.add(
        InlineKeyboardButton("👑 لیست ادمین", callback_data="admin_list"),
        InlineKeyboardButton("➕ افزودن ادمین", callback_data="admin_add")
    )
    
    if bot_status:
        markup.add(InlineKeyboardButton("🔴 خاموش کردن بات", callback_data="admin_bot_off"))
    else:
        markup.add(InlineKeyboardButton("🟢 روشن کردن بات", callback_data="admin_bot_on"))
    
    markup.add(
        InlineKeyboardButton("📊 آمار کامل", callback_data="admin_full_stats"),
        InlineKeyboardButton("🔄 ریست Webhook", callback_data="admin_reset_webhook")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
@admin_only
def admin_callbacks(call):
    if call.data == "admin_vip_list":
        vips = db.get_vip_list()
        if vips:
            text = "📋 **لیست VIPها:**\n\n"
            for vip in vips:
                user_id, username, name, expiry = vip
                expiry_date = expiry.split('T')[0] if expiry else "نامشخص"
                username_text = f"@{username}" if username and username != "None" else "بدون یوزرنیم"
                text += f"• {name} - `{user_id}`\n  👤 {username_text}\n  ⏳ انقضا: {expiry_date}\n\n"
        else:
            text = "📭 هیچ کاربر VIP وجود ندارد"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "admin_vip_add":
        msg = bot.send_message(call.message.chat.id, 
            "➕ **افزودن کاربر VIP**\n\n"
            "آیدی عددی کاربر را وارد کنید:")
        bot.register_next_step_handler(msg, process_vip_add)
    
    elif call.data == "admin_list":
        admins = db.get_admins()
        text = "👑 **لیست ادمین‌ها:**\n\n"
        for admin in admins:
            user_id, username, name = admin
            if user_id in SUPER_ADMINS:
                text += f"• {name} - `{user_id}` (👑 سوپر ادمین)\n"
            else:
                username_text = f"@{username}" if username and username != "None" and username != "super_admin" else "بدون یوزرنیم"
                text += f"• {name} - `{user_id}`\n  👤 {username_text}\n"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "admin_add":
        msg = bot.send_message(call.message.chat.id, 
            "➕ **افزودن ادمین جدید**\n\n"
            "آیدی عددی کاربر را وارد کنید:")
        bot.register_next_step_handler(msg, process_admin_add)
    
    elif call.data == "admin_bot_on":
        db.set_bot_status(True)
        bot.answer_callback_query(call.id, "✅ بات روشن شد!")
        stats = db.get_stats()
        text = (
            "👑 **پنل مدیریت**\n\n"
            f"📊 **آمار کلی:**\n"
            f"👥 کل کاربران: {stats['total_users']}\n"
            f"👑 ادمین‌ها: {stats['admin_users']}\n"
            f"💎 VIP: {stats['vip_users']}\n\n"
            f"⚡ **وضعیت بات:** 🟢 روشن"
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    elif call.data == "admin_bot_off":
        db.set_bot_status(False)
        bot.answer_callback_query(call.id, "✅ بات خاموش شد!")
        stats = db.get_stats()
        text = (
            "👑 **پنل مدیریت**\n\n"
            f"📊 **آمار کلی:**\n"
            f"👥 کل کاربران: {stats['total_users']}\n"
            f"👑 ادمین‌ها: {stats['admin_users']}\n"
            f"💎 VIP: {stats['vip_users']}\n\n"
            f"⚡ **وضعیت بات:** 🔴 خاموش"
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    elif call.data == "admin_full_stats":
        stats = db.get_stats()
        text = (
            "📊 **آمار کامل**\n\n"
            f"👥 کل کاربران: {stats['total_users']}\n"
            f"👑 ادمین‌ها: {stats['admin_users']}\n"
            f"💎 VIP: {stats['vip_users']}\n\n"
            f"📱 SMS درخواست: {stats['sms_requests']}\n"
            f"📞 تماس درخواست: {stats['call_requests']}\n"
            f"💎 ترکیبی درخواست: {stats['combo_requests']}\n"
            f"📊 کل درخواست: {stats['total_requests']}"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    
    elif call.data == "admin_reset_webhook":
        set_webhook()
        bot.answer_callback_query(call.id, "✅ Webhook ریست شد!")

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
        db.set_vip(user_id, days)
        
        try:
            bot.send_message(user_id, 
                f"💎 **تبریک! شما VIP شدید!**\n\n"
                f"✅ اشتراک {days} روزه فعال شد.\n"
                f"📊 محدودیت شما:\n"
                f"📱 SMS: {VIP_SMS_LIMIT} بار\n"
                f"📞 تماس: {VIP_CALL_LIMIT} بار\n"
                f"💎 ترکیبی: {VIP_COMBO_LIMIT} بار")
        except:
            pass
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} با {days} روز VIP شد!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

def process_admin_add(message):
    try:
        user_id = int(message.text.strip())
        
        if user_id in SUPER_ADMINS:
            bot.send_message(message.chat.id, "❌ این کاربر سوپر ادمین است و نیازی به افزودن ندارد!")
            return
        
        db.make_admin(user_id)
        
        try:
            bot.send_message(user_id, 
                f"👑 **تبریک! شما به جمع ادمین‌ها پیوستید!**\n\n"
                f"✅ اکنون به پنل مدیریت دسترسی دارید.")
        except:
            pass
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} با موفقیت ادمین شد!")
    except:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر است!")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    if message.chat.id in user_processes:
        user_processes[message.chat.id] = False
        bot.send_message(message.chat.id, "⛔ فرآیند متوقف شد.")
    else:
        bot.send_message(message.chat.id, "⚠️ فرآیندی در حال اجرا نیست.")

@bot.message_handler(func=lambda m: True)
@membership_required
def default_handler(message):
    bot.reply_to(
        message, 
        "❌ دستور نامعتبر!\nاز دکمه‌های منوی ربات استفاده کنید."
    )

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🚀 SMS + Call + Combo Bomber Bot - نسخه نهایی")
    print("="*60)
    print("👨‍💻 سازنده: top_topy_messenger_bot\n@")
    print("📢 کانال پشتیبانی: death_star_sms_bomber\n\n@")
    print(f"👑 سوپر ادمین‌ها: {SUPER_ADMINS}")
    print(f"📱 SMS: همه کاربران (محدودیت {NORMAL_SMS_LIMIT})")
    print(f"📞 CALL: فقط VIP (محدودیت {VIP_CALL_LIMIT})")
    print(f"💎 COMBO: فقط VIP (محدودیت {VIP_COMBO_LIMIT})")
    print(f"🌐 آدرس لیارا: {LIARA_API_URL}")
    print("="*60)
    
    # ترد زنده نگه داشتن
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("✅ ترد زنده نگه داشتن فعال شد")
    
    # تنظیم webhook
    set_webhook()
    
    # اجرا
    print(f"🚀 اجرا روی پورت {PORT}")
    app.run(host='0.0.0.0', port=PORT)
