# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import threading
import time
from datetime import datetime, timedelta
import re
import os
import sqlite3
import hashlib
from flask import Flask, request

# ========== تنظیمات اصلی (از متغیر محیطی) ==========
TOKEN = os.environ.get("BOT_TOKEN")  # ✅ تغییر کرد - مقدار پیش‌فرض پاک شد
ADMIN_IDS = [8226091292, 8503492459]
LIARA_API = os.environ.get("LIARA_API")  # ✅ تغییر کرد - مقدار پیش‌فرض پاک شد

# ========== تعریف بات (قبل از هر چیز) ==========
bot = telebot.TeleBot(TOKEN)

# ========== کانال و گروه‌های اجباری ==========
REQUIRED_CHANNELS = [
    {"name": "کانال اصلی", "url": "https://t.me/top_topy_bomber", "username": "@top_topy_bomber"},
    {"name": "گروه لس آنجلس", "url": "https://t.me/+c5sZUJHnC8MxOGM0", "username": None},
    {"name": "گروه دوم", "url": "https://t.me/BHOPYTNEAK", "username": "@BHOPYTNEAK"},
    {"name": "گروه اینترنت آزاد", "url": "https://t.me/internetazad4", "username": "@internetazad4"}
]
CREATOR_USERNAME = "@top_topy_bombe"

# ========== شماره‌های مسدود شده (به صورت هش - بدون افشای شماره) ==========
BLOCKED_PHONE_HASHES = [
    "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # هش شماره 1
    "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"   # هش شماره 2
]

# ========== لیست VIPها (بدون افشا) ==========
VIP_USERS = [
    8226091292,
    8503492459,
]

# ========== متغیرها ==========
user_states = {}
active_attacks = {}
DAILY_LIMIT_NORMAL = 5
DAILY_LIMIT_VIP = 20
bot_active = True

# ========== راه‌اندازی دیتابیس SQLite ==========
def init_database():
    """ایجاد جداول دیتابیس"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # جدول آمار روزانه کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS user_daily
                 (user_id INTEGER PRIMARY KEY, 
                  date TEXT,
                  count INTEGER)''')
    
    # جدول تعداد پیام‌های کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS user_messages
                 (user_id INTEGER PRIMARY KEY,
                  count INTEGER)''')
    
    # جدول آخرین استفاده
    c.execute('''CREATE TABLE IF NOT EXISTS user_last_use
                 (user_id INTEGER PRIMARY KEY,
                  last_use INTEGER)''')
    
    # جدول ادمین‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (user_id INTEGER PRIMARY KEY)''')
    
    conn.commit()
    conn.close()
    
    # اضافه کردن ادمین‌های اولیه
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    for admin_id in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
    conn.commit()
    conn.close()

# ========== توابع کار با دیتابیس ==========
def get_user_daily(user_id):
    """گرفتن آمار روزانه کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    
    c.execute("SELECT count FROM user_daily WHERE user_id = ? AND date = ?", 
              (user_id, today))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0

def update_user_daily(user_id, count):
    """به‌روزرسانی آمار روزانه کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    
    c.execute("INSERT OR REPLACE INTO user_daily (user_id, date, count) VALUES (?, ?, ?)",
              (user_id, today, count))
    conn.commit()
    conn.close()

def increment_user_daily(user_id):
    """افزایش یک واحد به آمار روزانه کاربر"""
    current = get_user_daily(user_id)
    update_user_daily(user_id, current + 1)

def get_user_messages_count(user_id):
    """گرفتن تعداد کل پیام‌های کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("SELECT count FROM user_messages WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0

def increment_user_messages(user_id):
    """افزایش تعداد پیام‌های کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current = get_user_messages_count(user_id)
    
    c.execute("INSERT OR REPLACE INTO user_messages (user_id, count) VALUES (?, ?)",
              (user_id, current + 1))
    conn.commit()
    conn.close()

def get_user_last_use(user_id):
    """گرفتن آخرین زمان استفاده کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("SELECT last_use FROM user_last_use WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0

def set_user_last_use(user_id, timestamp):
    """تنظیم آخرین زمان استفاده کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("INSERT OR REPLACE INTO user_last_use (user_id, last_use) VALUES (?, ?)",
              (user_id, timestamp))
    conn.commit()
    conn.close()

# ========== توابع مدیریت ادمین ==========
def is_admin(user_id):
    """بررسی ادمین بودن کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_all_admins():
    """دریافت لیست همه ادمین‌ها"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    results = [row[0] for row in c.fetchall()]
    conn.close()
    return results

def add_admin(user_id):
    """افزودن ادمین جدید"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    """حذف ادمین"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ========== توابع کمکی ==========
def is_vip(user_id):
    return user_id in VIP_USERS

def get_daily_limit(user_id):
    return DAILY_LIMIT_VIP if is_vip(user_id) else DAILY_LIMIT_NORMAL

def check_daily_limit(user_id):
    """بررسی محدودیت روزانه"""
    today_used = get_user_daily(user_id)
    limit = get_daily_limit(user_id)
    return today_used < limit

def hash_phone(phone):
    """هش کردن شماره تلفن برای مقایسه امن"""
    return hashlib.sha256(phone.encode()).hexdigest()

def is_phone_blocked(phone):
    """بررسی مسدود بودن شماره با مقایسه هش"""
    phone_hash = hash_phone(phone)
    return phone_hash in BLOCKED_PHONE_HASHES

# ========== تابع ارسال پیام عضویت ==========
def send_membership_message(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        btn = types.InlineKeyboardButton(f"📢 {ch['name']}", url=ch['url'])
        markup.add(btn)
    
    bot.send_message(
        chat_id,
        "🔰 **برای استفاده از ربات، لطفاً عضو شو!**\n\n"
        "با عضویت در کانال و گروه‌های ما، از آخرین اخبار و آموزش‌ها باخبر میشی.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# ========== خوش‌آمدگویی ==========
def get_welcome_message(user):
    name = user.first_name or "عزیز"
    today_used = get_user_daily(user.id)
    limit = get_daily_limit(user.id)
    vip_status = "⭐ VIP" if is_vip(user.id) else "👤 عادی"
    
    return f"""🎯 **به ربات اس ام اس بمبر خوش اومدی {name}!**

🔥 **ساخته شده توسط {CREATOR_USERNAME}**
{vip_status}
📊 استفاده امروز: {today_used}/{limit}

📱 **قابلیت‌ها:**
• ارسال پیامک به بیش از ۲۰۰ سرویس ایرانی
• محدودیت روزانه: {limit} بار
• گزارش لحظه‌ای از تعداد پیامک‌های ارسالی
• قابلیت توقف حمله در هر لحظه

🔽 برای شروع از دکمه‌های زیر استفاده کن.
"""

# ========== استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    global bot_active
    user_id = message.from_user.id
    
    if not bot_active and not is_admin(user_id):
        bot.reply_to(message, "⛔ ربات در حال حاضر غیرفعال است.")
        return
    
    increment_user_messages(user_id)
    
    # ارسال پیام عضویت
    send_membership_message(message.chat.id)
    
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🚀 حمله جدید')
    btn2 = types.KeyboardButton('📊 وضعیت من')
    btn3 = types.KeyboardButton('📈 آمار کلی')
    btn4 = types.KeyboardButton('⛔ توقف حمله')
    btn5 = types.KeyboardButton('📞 ارتباط با سازنده')
    
    if is_admin(user_id):
        btn6 = types.KeyboardButton('👑 پنل مدیریت')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    else:
        markup.add(btn1, btn2, btn3, btn4, btn5)
    
    bot.send_message(message.chat.id, get_welcome_message(message.from_user), reply_markup=markup, parse_mode="Markdown")

# ========== وضعیت من ==========
@bot.message_handler(func=lambda m: m.text == '📊 وضعیت من')
def my_status(m):
    user_id = m.chat.id
    today_used = get_user_daily(user_id)
    limit = get_daily_limit(user_id)
    vip_status = "⭐ VIP" if is_vip(user_id) else "👤 عادی"
    last_use = get_user_last_use(user_id)
    
    status_text = f"""📊 **وضعیت شما:**

👤 کاربر: {m.from_user.first_name}
{vip_status}
📅 استفاده امروز: {today_used} بار
✅ باقیمانده: {limit - today_used} بار
⚡ محدودیت روزانه: {limit} بار
"""
    
    if user_id in active_attacks and active_attacks[user_id]:
        status_text += "\n⚠️ **حمله در حال انجام هست!**"
    else:
        status_text += "\n✅ **آماده برای حمله جدیدی!**"
    
    if last_use:
        time_diff = int(time.time() - last_use)
        if time_diff < 120:
            wait = 120 - time_diff
            status_text += f"\n⏳ زمان انتظار تا حمله بعد: {wait} ثانیه"
    
    status_text += f"\n\n👑 {CREATOR_USERNAME}"
    
    bot.reply_to(m, status_text, parse_mode="Markdown")

# ========== آمار کلی ==========
@bot.message_handler(func=lambda m: m.text == '📈 آمار کلی')
def global_stats(m):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM user_daily")
    total_users = c.fetchone()[0]
    
    today = datetime.now().date().isoformat()
    c.execute("SELECT COUNT(*) FROM user_daily WHERE date = ?", (today,))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(count) FROM user_messages")
    total_messages = c.fetchone()[0] or 0
    
    conn.close()
    
    vip_count = len(VIP_USERS)
    
    msg = f"""📊 **آمار کلی ربات:**

👥 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⭐ کاربران VIP: {vip_count}
📨 کل درخواست‌ها: {total_messages}
⚡ محدودیت عادی: {DAILY_LIMIT_NORMAL} بار
⚡ محدودیت VIP: {DAILY_LIMIT_VIP} بار

👑 **ساخته شده توسط {CREATOR_USERNAME}**"""
    
    bot.reply_to(m, msg, parse_mode="Markdown")

# ========== حمله جدید ==========
@bot.message_handler(func=lambda m: m.text == '🚀 حمله جدید')
def new_attack(m):
    global bot_active
    user_id = m.chat.id
    limit = get_daily_limit(user_id)
    
    if not bot_active and not is_admin(user_id):
        bot.reply_to(m, "⛔ ربات غیرفعال است.")
        return
    
    # بررسی محدودیت روزانه
    if not check_daily_limit(user_id) and not is_admin(user_id):
        bot.reply_to(m, f"⚠️ محدودیت روزانه تموم شد! فردا {limit} بار دیگه می‌تونی استفاده کنی.")
        return
    
    # بررسی فاصله زمانی
    last_use = get_user_last_use(user_id)
    if last_use:
        time_diff = int(time.time() - last_use)
        if time_diff < 120 and not is_admin(user_id):
            remaining = 120 - time_diff
            bot.reply_to(m, f"⏳ {remaining} ثانیه صبر کن بین هر حمله.")
            return
    
    # بررسی حمله فعال
    if user_id in active_attacks and active_attacks[user_id]:
        bot.reply_to(m, "⚠️ الان یه حمله فعال داری! اول تموم شه بعد دوباره تلاش کن.")
        return
    
    user_states[user_id] = "waiting_for_phone"
    today_used = get_user_daily(user_id)
    remaining = limit - today_used
    bot.reply_to(m, f"📱 **شماره موبایل رو بفرست:**\n(مثلاً 09123456789)\n📊 باقیمانده امروز: {remaining} بار")

# ========== دریافت شماره ==========
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "waiting_for_phone")
def get_phone(m):
    user_id = m.chat.id
    phone = m.text.strip()
    
    if not re.match(r'^09\d{9}$', phone):
        bot.reply_to(m, "❌ شماره نامعتبر! باید ۱۱ رقم و با ۰۹ شروع بشه.")
        del user_states[user_id]
        return
    
    # بررسی شماره‌های مسدود شده با هش
    if is_phone_blocked(phone):
        bot.reply_to(m, "❌ خطای 404: شماره مورد نظر یافت نشد.")
        del user_states[user_id]
        return
    
    del user_states[user_id]
    set_user_last_use(user_id, int(time.time()))
    active_attacks[user_id] = True
    
    # ثبت آمار
    increment_user_daily(user_id)
    
    today_used = get_user_daily(user_id)
    limit = get_daily_limit(user_id)
    remaining = limit - today_used
    
    msg = bot.reply_to(
        m, 
        f"✅ شماره {phone} دریافت شد.\n🔥 در حال ارسال پیامک...\n📊 باقیمانده امروز: {remaining} بار"
    )
    
    threading.Thread(target=run_attack, args=(phone, user_id, msg.message_id)).start()

# ========== اجرای حمله ==========
def run_attack(phone, chat_id, msg_id):
    try:
        response = requests.post(LIARA_API, json={'phone': phone}, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            result = data.get('result', {})
            success = result.get('success', 0)
            total = result.get('total', 0)
            percent = int((success / total) * 100) if total > 0 else 0
            
            final_msg = f"""✅ **حمله با موفقیت انجام شد!**

📱 شماره: {phone[:4]}****{phone[-4:]}  # مخفی کردن بخشی از شماره
✅ موفق: {success}
❌ ناموفق: {total - success}
📊 مجموع: {total}
📈 درصد موفقیت: {percent}%

👑 {CREATOR_USERNAME}"""
            
            bot.edit_message_text(final_msg, chat_id, msg_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ خطا در حمله (پاسخ ناموفق از سرور)", chat_id, msg_id)
    except requests.exceptions.Timeout:
        bot.edit_message_text("❌ خطا: زمان درخواست به پایان رسید. لطفاً دقایقی بعد تلاش کنید.", chat_id, msg_id)
    except requests.exceptions.ConnectionError:
        bot.edit_message_text("❌ خطا: مشکل در اتصال به سرور.", chat_id, msg_id)
    except requests.exceptions.HTTPError as e:
        bot.edit_message_text(f"❌ خطای HTTP: {e.response.status_code}", chat_id, msg_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطای غیرمنتظره: {str(e)}", chat_id, msg_id)
    finally:
        if chat_id in active_attacks:
            del active_attacks[chat_id]

# ========== توقف حمله ==========
@bot.message_handler(func=lambda m: m.text == '⛔ توقف حمله')
def stop_attack(m):
    user_id = m.chat.id
    if user_id in active_attacks:
        active_attacks[user_id] = False
        bot.reply_to(m, "⛔ حمله متوقف شد.")
    else:
        bot.reply_to(m, "❌ حمله فعالی نیست.")

# ========== پنل مدیریت ==========
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت' and is_admin(m.from_user.id))
def admin_panel(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 آمار مدیریت', '📋 لیست VIPها', '🔴 خاموش/روشن', '📋 گزارش کاربران')
    markup.add('👥 مدیریت ادمین‌ها', '🔙 برگشت')
    bot.reply_to(m, "👑 پنل مدیریت:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📊 آمار مدیریت' and is_admin(m.from_user.id))
def admin_stats(m):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM user_daily")
    total_users = c.fetchone()[0]
    
    today = datetime.now().date().isoformat()
    c.execute("SELECT COUNT(*) FROM user_daily WHERE date = ?", (today,))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(count) FROM user_messages")
    total_messages = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM user_daily WHERE count > 0")
    active_users = c.fetchone()[0]
    
    conn.close()
    
    active_attacks_count = len([x for x in active_attacks.values() if x])
    status = "✅ فعال" if bot_active else "❌ غیرفعال"
    vip_count = len(VIP_USERS)
    admins = get_all_admins()
    admin_count = len(admins)
    
    msg = f"""📊 **آمار مدیریت:**
    
👤 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⚡ کاربران فعال: {active_users}
⭐ VIPها: {vip_count}
👑 ادمین‌ها: {admin_count}
⚡ حملات هم‌اکنون: {active_attacks_count}
📨 کل پیام‌ها: {total_messages}
🔰 وضعیت ربات: {status}
👑 سازنده: {CREATOR_USERNAME}
"""
    bot.reply_to(m, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '📋 لیست VIPها' and is_admin(m.from_user.id))
def vip_list(m):
    if not VIP_USERS:
        bot.reply_to(m, "📋 لیست VIPها خالی هست.")
        return
    
    text = "📋 **لیست VIPها:**\n\n"
    for uid in VIP_USERS:
        text += f"👤 `{uid}`\n"
    text += f"\n👑 {CREATOR_USERNAME}"
    bot.reply_to(m, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '🔴 خاموش/روشن' and is_admin(m.from_user.id))
def admin_toggle(m):
    global bot_active
    bot_active = not bot_active
    status = "روشن" if bot_active else "خاموش"
    bot.reply_to(m, f"✅ ربات {status} شد.")

@bot.message_handler(func=lambda m: m.text == '📋 گزارش کاربران' and is_admin(m.from_user.id))
def admin_users(m):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    
    c.execute('''SELECT user_id, count FROM user_daily 
                 WHERE date = ? ORDER BY count DESC LIMIT 10''', (today,))
    users = c.fetchall()
    conn.close()
    
    report = "📋 **کاربران برتر امروز:**\n\n"
    for uid, count in users:
        vip = "⭐" if is_vip(uid) else "👤"
        report += f"{vip} `{uid}`: {count} حمله\n"
    report += f"\n👑 {CREATOR_USERNAME}"
    bot.reply_to(m, report, parse_mode="Markdown")

# ========== مدیریت ادمین‌ها ==========
@bot.message_handler(func=lambda m: m.text == '👥 مدیریت ادمین‌ها' and is_admin(m.from_user.id))
def manage_admins(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('➕ افزودن ادمین', '➖ حذف ادمین', '📋 لیست ادمین‌ها', '🔙 برگشت')
    bot.reply_to(m, "👥 مدیریت ادمین‌ها:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📋 لیست ادمین‌ها' and is_admin(m.from_user.id))
def list_admins(m):
    admins = get_all_admins()
    if not admins:
        bot.reply_to(m, "📋 هیچ ادمینی یافت نشد.")
        return
    
    text = "📋 **لیست ادمین‌ها:**\n\n"
    for uid in admins:
        text += f"👑 `{uid}`\n"
    text += f"\n👑 {CREATOR_USERNAME}"
    bot.reply_to(m, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == '➕ افزودن ادمین' and is_admin(m.from_user.id))
def add_admin_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی کاربر مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_add_admin", msg.message_id)

@bot.message_handler(func=lambda m: m.text == '➖ حذف ادمین' and is_admin(m.from_user.id))
def remove_admin_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی ادمین مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_remove_admin", msg.message_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) and user_states[m.chat.id][0] in ["waiting_for_add_admin", "waiting_for_remove_admin"])
def handle_admin_edit(m):
    state = user_states.get(m.chat.id)
    if not state:
        return
    
    user_id_str = m.text.strip()
    if not user_id_str.isdigit():
        bot.reply_to(m, "❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    target_id = int(user_id_str)
    
    if state[0] == "waiting_for_add_admin":
        add_admin(target_id)
        bot.reply_to(m, f"✅ کاربر {target_id} با موفقیت به ادمین‌ها اضافه شد.")
    elif state[0] == "waiting_for_remove_admin":
        if target_id in ADMIN_IDS:
            bot.reply_to(m, "❌ این کاربر جزو ادمین‌های ثابت است و قابل حذف نیست.")
        else:
            remove_admin(target_id)
            bot.reply_to(m, f"✅ کاربر {target_id} از ادمین‌ها حذف شد.")
    
    del user_states[m.chat.id]

@bot.message_handler(func=lambda m: m.text == '🔙 برگشت' and is_admin(m.from_user.id))
def admin_back(m):
    start(m)

# ========== ارتباط با سازنده ==========
@bot.message_handler(func=lambda m: m.text == '📞 ارتباط با سازنده')
def contact(m):
    markup = types.ForceReply(selective=False)
    msg = bot.reply_to(
        m, 
        f"📝 **پیامت رو بنویس، برات می‌فرستم برای سازنده:**\n\n👑 {CREATOR_USERNAME}",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    user_states[m.chat.id] = ("waiting_for_contact", msg.message_id)

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) and user_states[m.chat.id][0] == "waiting_for_contact")
def handle_contact_message(m):
    state = user_states.get(m.chat.id)
    if not state:
        return
    
    vip = "⭐ VIP" if is_vip(m.from_user.id) else "👤 عادی"
    user_info = f"از: {m.from_user.first_name} (ID: {m.from_user.id})\nوضعیت: {vip}"
    
    del user_states[m.chat.id]
    
    admins = get_all_admins()
    for admin_id in admins:
        try:
            bot.send_message(
                admin_id,
                f"📨 **پیام جدید از کاربر:**\n\n{user_info}\n\n📝 {m.text}\n\n👑 {CREATOR_USERNAME}",
                parse_mode="Markdown"
            )
        except:
            pass
    
    bot.reply_to(m, f"✅ پیامت با موفقیت ارسال شد. به زودی پاسخ می‌دم.\n👑 {CREATOR_USERNAME}")

# ========== پیام‌های ناشناخته ==========
@bot.message_handler(func=lambda m: True)
def fallback(m):
    if user_states.get(m.chat.id):
        return
    
    valid_buttons = ['🚀 حمله جدید', '📊 وضعیت من', '📈 آمار کلی', '⛔ توقف حمله', 
                     '📞 ارتباط با سازنده', '👑 پنل مدیریت', '📊 آمار مدیریت', 
                     '📋 لیست VIPها', '🔴 خاموش/روشن', '📋 گزارش کاربران', 
                     '👥 مدیریت ادمین‌ها', '➕ افزودن ادمین', '➖ حذف ادمین', 
                     '📋 لیست ادمین‌ها', '🔙 برگشت']
    
    if m.text in valid_buttons:
        return
    
    bot.reply_to(m, "⚠️ لطفاً از دکمه‌های منو استفاده کن.")

# ========== تنظیم Flask برای Webhook ==========
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

@app.route('/setwebhook')
def set_webhook():
    webhook_url = f"https://top-topye.onrender.com/webhook"
    bot.remove_webhook()
    time.sleep(1)
    success = bot.set_webhook(url=webhook_url)
    
    if success:
        return f"✅ Webhook set to {webhook_url}", 200
    else:
        return "❌ Failed to set webhook", 400

@app.route('/')
def index():
    return f"ربات اس ام اس بمبر فعال است ✅\n👑 سازنده: {CREATOR_USERNAME}", 200

# ========== اجرا ==========
if __name__ == "__main__":
    # ایجاد دیتابیس
    init_database()
    
    print("🤖 ربات با SQLite راه‌اندازی شد")
    print(f"👑 سازنده: {CREATOR_USERNAME}")
    print("✅ شماره‌های مسدود شده به صورت هش ذخیره شده‌اند")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
