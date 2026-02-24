# -*- coding: utf-8 -*-
"""
🤖 ربات ماشین حساب شیشه‌ای - نسخه VIP
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
import math

# ==================== تنظیمات اصلی ====================

BOT_TOKEN = "8098018364:AAGcNlQ7SSOKewFdwRCUfz4PuA4PpRmcj3Y"
ADMIN_IDS = [7620484201, 8226091292]
REQUIRED_CHANNEL = "@death_star_sms_bomber"
CHANNEL_LINK = "https://t.me/death_star_sms_bomber"

# اطلاعات سازنده
DEVELOPER_USERNAME = "top_topy_messenger_bot"
DEVELOPER_ID = 7620484201
SUPPORT_CHANNEL = "@death_star_sms_bomber"

# اسم سرویس رندر
SERVICE_NAME = "ftyydftrye5r-6e5te"
BASE_URL = f"https://{SERVICE_NAME}.onrender.com"
WEBHOOK_URL = f"{BASE_URL}/webhook"

# ==================== مقداردهی اولیه ====================

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)

# ذخیره موقت عملیات کاربران
user_data = {}

# ==================== صفحات وب ====================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    except Exception as e:
        return 'Error', 500

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>ربات ماشین حساب شیشه‌ای</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    font-family: 'Vazir', 'Segoe UI', Tahoma, sans-serif;
                    min-height: 100vh;
                    background: linear-gradient(145deg, #1a1c2c 0%, #2a2f4f 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    padding: 20px;
                }
                
                .glass-panel {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(15px);
                    -webkit-backdrop-filter: blur(15px);
                    border-radius: 40px;
                    padding: 40px;
                    box-shadow: 
                        0 25px 50px -12px rgba(0, 0, 0, 0.5),
                        inset 0 -2px 2px rgba(255, 255, 255, 0.1),
                        inset 0 2px 2px rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    width: 100%;
                    max-width: 600px;
                }
                
                h1 {
                    color: white;
                    font-size: 2.5em;
                    margin-bottom: 10px;
                    text-align: center;
                    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
                    font-weight: 500;
                }
                
                .subtitle {
                    color: rgba(255, 255, 255, 0.7);
                    text-align: center;
                    margin-bottom: 40px;
                    font-size: 1.1em;
                }
                
                .calculator-preview {
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 30px;
                    padding: 30px;
                    margin: 30px 0;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .display {
                    background: rgba(0, 0, 0, 0.5);
                    border-radius: 20px;
                    padding: 20px;
                    margin-bottom: 20px;
                    text-align: right;
                    color: white;
                    font-size: 2em;
                    font-family: 'Courier New', monospace;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.3);
                }
                
                .buttons-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 10px;
                }
                
                .calc-btn {
                    background: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    padding: 20px;
                    color: white;
                    font-size: 1.3em;
                    font-weight: bold;
                    cursor: pointer;
                    transition: all 0.2s;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                
                .calc-btn:hover {
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-2px);
                }
                
                .operator-btn {
                    background: linear-gradient(145deg, #ff6b6b, #ff4757);
                    border: none;
                    color: white;
                }
                
                .equal-btn {
                    background: linear-gradient(145deg, #51cf66, #37b24d);
                    border: none;
                    grid-column: span 2;
                }
                
                .stats {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin: 40px 0;
                }
                
                .stat-card {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 25px;
                    padding: 25px;
                    text-align: center;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    backdrop-filter: blur(10px);
                }
                
                .stat-number {
                    font-size: 2.5em;
                    color: #ffd700;
                    font-weight: bold;
                }
                
                .stat-label {
                    color: rgba(255, 255, 255, 0.7);
                    margin-top: 10px;
                }
                
                .developer-info {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 25px;
                    padding: 25px;
                    margin-top: 40px;
                    text-align: center;
                }
                
                .developer-info h3 {
                    color: white;
                    font-size: 1.5em;
                    margin-bottom: 10px;
                }
                
                .developer-info p {
                    color: rgba(255, 255, 255, 0.9);
                }
                
                .developer-info a {
                    color: #ffd700;
                    text-decoration: none;
                }
                
                .developer-info a:hover {
                    text-decoration: underline;
                }
                
                .features {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    justify-content: center;
                    margin: 30px 0;
                }
                
                .feature-tag {
                    background: rgba(255, 255, 255, 0.15);
                    border-radius: 50px;
                    padding: 12px 25px;
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    font-size: 1em;
                }
            </style>
        </head>
        <body>
            <div class="glass-panel">
                <h1>🧮 ماشین حساب شیشه‌ای</h1>
                <div class="subtitle">✨ محاسبات سریع و دقیق با طراحی مدرن</div>
                
                <div class="calculator-preview">
                    <div class="display">0</div>
                    <div class="buttons-grid">
                        <button class="calc-btn">7</button>
                        <button class="calc-btn">8</button>
                        <button class="calc-btn">9</button>
                        <button class="calc-btn operator-btn">÷</button>
                        <button class="calc-btn">4</button>
                        <button class="calc-btn">5</button>
                        <button class="calc-btn">6</button>
                        <button class="calc-btn operator-btn">×</button>
                        <button class="calc-btn">1</button>
                        <button class="calc-btn">2</button>
                        <button class="calc-btn">3</button>
                        <button class="calc-btn operator-btn">-</button>
                        <button class="calc-btn">0</button>
                        <button class="calc-btn">.</button>
                        <button class="calc-btn operator-btn">+</button>
                        <button class="calc-btn">C</button>
                    </div>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">∞</div>
                        <div class="stat-label">محاسبات نامحدود</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">⚡</div>
                        <div class="stat-label">پاسخ فوری</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">🔮</div>
                        <div class="stat-label">طراحی شیشه‌ای</div>
                    </div>
                </div>
                
                <div class="features">
                    <span class="feature-tag">➕ جمع</span>
                    <span class="feature-tag">➖ تفریق</span>
                    <span class="feature-tag">✖️ ضرب</span>
                    <span class="feature-tag">➗ تقسیم</span>
                    <span class="feature-tag">📊 درصد</span>
                    <span class="feature-tag">√ رادیکال</span>
                    <span class="feature-tag">^ توان</span>
                    <span class="feature-tag">() پرانتز</span>
                </div>
                
                <div class="developer-info">
                    <h3>👨‍💻 سازنده: @top_topy_messenger_bot</h3>
                    <p>📢 کانال پشتیبانی: @death_star_sms_bomber</p>
                    <p style="margin-top: 15px;">🤖 برای استفاده از ربات، به تلگرام بروید و دستور /start را بزنید</p>
                </div>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {
        "status": "healthy",
        "service": "glass-calculator-bot",
        "developer": f"@{DEVELOPER_USERNAME}",
        "support": SUPPORT_CHANNEL,
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

# ==================== توابع ماشین حساب ====================

def calculate(expression):
    """محاسبه عبارت ریاضی"""
    try:
        # پاکسازی عبارت
        expression = expression.replace(' ', '')
        expression = expression.replace('×', '*')
        expression = expression.replace('÷', '/')
        expression = expression.replace('^', '**')
        expression = expression.replace('√', 'sqrt')
        expression = expression.replace('%', '/100')
        
        # محاسبه با eval (با احتیاط)
        result = eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log, "pi": math.pi, "e": math.e})
        
        # گرد کردن نتیجه
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        return True, result
    except ZeroDivisionError:
        return False, "❌ تقسیم بر صفر امکان‌پذیر نیست!"
    except Exception as e:
        return False, f"❌ خطا در محاسبه: {str(e)[:50]}"

# ==================== کیبورد ماشین حساب ====================

def get_calculator_keyboard():
    """ایجاد کیبورد شیشه‌ای ماشین حساب"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    
    # ردیف اول
    markup.add(
        KeyboardButton("C"), KeyboardButton("("), KeyboardButton(")"), KeyboardButton("÷")
    )
    
    # ردیف دوم
    markup.add(
        KeyboardButton("7"), KeyboardButton("8"), KeyboardButton("9"), KeyboardButton("×")
    )
    
    # ردیف سوم
    markup.add(
        KeyboardButton("4"), KeyboardButton("5"), KeyboardButton("6"), KeyboardButton("-")
    )
    
    # ردیف چهارم
    markup.add(
        KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3"), KeyboardButton("+")
    )
    
    # ردیف پنجم
    markup.add(
        KeyboardButton("0"), KeyboardButton("."), KeyboardButton("%"), KeyboardButton("=")
    )
    
    # ردیف ششم (عملیات پیشرفته)
    markup.add(
        KeyboardButton("√"), KeyboardButton("^"), KeyboardButton("π"), KeyboardButton("e")
    )
    
    # ردیف هفتم
    markup.add(
        KeyboardButton("📊 راهنما"), KeyboardButton("🗑 پاک کردن"), KeyboardButton("📞 پشتیبانی")
    )
    
    return markup

def get_scientific_keyboard():
    """کیبورد علمی پیشرفته"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    
    markup.add(
        KeyboardButton("sin"), KeyboardButton("cos"), KeyboardButton("tan"), KeyboardButton("log")
    )
    
    markup.add(
        KeyboardButton("asin"), KeyboardButton("acos"), KeyboardButton("atan"), KeyboardButton("ln")
    )
    
    markup.add(
        KeyboardButton("!"), KeyboardButton("√"), KeyboardButton("^2"), KeyboardButton("^3")
    )
    
    markup.add(
        KeyboardButton("1/x"), KeyboardButton("|x|"), KeyboardButton("exp"), KeyboardButton("mod")
    )
    
    markup.add(
        KeyboardButton("🔙 بازگشت"), KeyboardButton("🧮 ماشین حساب")
    )
    
    return markup

# ==================== هندلرهای بات ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # ذخیره وضعیت کاربر
    user_data[user_id] = {
        "expression": "",
        "last_result": 0,
        "mode": "standard"
    }
    
    markup = get_calculator_keyboard()
    
    welcome = (
        "🧮 **به ماشین حساب شیشه‌ای خوش آمدید!**\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}\n"
        f"📢 **کانال پشتیبانی:** {SUPPORT_CHANNEL}\n\n"
        "✨ **قابلیت‌ها:**\n"
        "• محاسبات پایه (جمع، تفریق، ضرب، تقسیم)\n"
        "• عملیات علمی (سینوس، کسینوس، لگاریتم)\n"
        "• توان و رادیکال\n"
        "• درصد و پرانتز\n"
        "• طراحی شیشه‌ای و مدرن\n\n"
        "🔰 **برای شروع، اعداد و عملیات را وارد کنید:**"
    )
    
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['scientific'])
def scientific_mode(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    else:
        user_data[user_id]["mode"] = "scientific"
    
    bot.send_message(
        message.chat.id,
        "🔬 **حالت علمی فعال شد**\n\nاز دکمه‌های زیر برای محاسبات پیشرفته استفاده کنید:",
        parse_mode="Markdown",
        reply_markup=get_scientific_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "🧮 ماشین حساب")
def back_to_calculator(message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["mode"] = "standard"
        user_data[user_id]["expression"] = ""
    
    bot.send_message(
        message.chat.id,
        "🧮 **به ماشین حساب بازگشتید**",
        parse_mode="Markdown",
        reply_markup=get_calculator_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت")
def back_from_scientific(message):
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["mode"] = "standard"
        user_data[user_id]["expression"] = ""
    
    bot.send_message(
        message.chat.id,
        "🧮 **به ماشین حساب بازگشتید**",
        parse_mode="Markdown",
        reply_markup=get_calculator_keyboard()
    )

@bot.message_handler(func=lambda m: m.text == "📊 راهنما")
def help_handler(message):
    help_text = (
        "📚 **راهنمای استفاده از ماشین حساب**\n\n"
        "**🔹 عملیات پایه:**\n"
        "• جمع: + (یا دکمه +)\n"
        "• تفریق: - (یا دکمه -)\n"
        "• ضرب: × (یا دکمه ×)\n"
        "• تقسیم: ÷ (یا دکمه ÷)\n\n"
        "**🔸 عملیات پیشرفته:**\n"
        "• توان: ^ (مثال: 2^3 = 8)\n"
        "• رادیکال: √ (مثال: √9 = 3)\n"
        "• درصد: % (مثال: 20% از 200 = 40)\n"
        "• پرانتز: ( ) برای اولویت‌بندی\n\n"
        "**🔹 توابع علمی:**\n"
        "• sin, cos, tan, log, ln\n"
        "• asin, acos, atan (معکوس)\n"
        "• ! فاکتوریل\n"
        "• π عدد پی\n"
        "• e عدد نپر\n\n"
        "**🔸 نکات:**\n"
        "• برای محاسبه، بعد از وارد کردن عبارت، روی = کلیک کنید\n"
        "• دکمه C برای پاک کردن کل عبارت\n"
        "• دکمه 🗑 پاک کردن برای حذف آخرین کاراکتر\n"
        "• نتیجه آخرین محاسبه در حافظه ذخیره می‌شود\n\n"
        f"👨‍💻 **سازنده:** @{DEVELOPER_USERNAME}"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗑 پاک کردن")
def clear_handler(message):
    user_id = message.from_user.id
    if user_id in user_data:
        expr = user_data[user_id].get("expression", "")
        if expr:
            user_data[user_id]["expression"] = expr[:-1]
            current = user_data[user_id]["expression"] or "0"
            bot.send_message(message.chat.id, f"📝 **عبارت فعلی:** `{current}`", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ هیچ عبارتی وجود ندارد!")
    else:
        bot.send_message(message.chat.id, "⚠️ ابتدا /start را بزنید!")

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

@bot.message_handler(func=lambda m: m.text in ["sin", "cos", "tan", "log", "ln", "asin", "acos", "atan"])
def trig_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    func = message.text
    last_result = user_data[user_id].get("last_result", 0)
    
    msg = bot.send_message(
        message.chat.id,
        f"🔢 عدد را برای تابع {func} وارد کنید (پیش‌فرض: {last_result}):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_trig, user_id, func, last_result)

def process_trig(message, user_id, func, default_value):
    try:
        text = message.text.strip()
        if text == "":
            value = default_value
        else:
            value = float(text.replace(',', '.'))
        
        result = None
        if func == "sin":
            result = math.sin(math.radians(value))
        elif func == "cos":
            result = math.cos(math.radians(value))
        elif func == "tan":
            result = math.tan(math.radians(value))
        elif func == "log":
            result = math.log10(value)
        elif func == "ln":
            result = math.log(value)
        elif func == "asin":
            result = math.degrees(math.asin(value))
        elif func == "acos":
            result = math.degrees(math.acos(value))
        elif func == "atan":
            result = math.degrees(math.atan(value))
        
        if result is not None:
            # گرد کردن نتیجه
            if abs(result - round(result, 10)) < 1e-10:
                result = round(result, 10)
            
            user_data[user_id]["last_result"] = result
            bot.send_message(
                message.chat.id,
                f"✅ **نتیجه:** `{result}`",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ خطا در محاسبه!")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "!")
def factorial_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    last_result = user_data[user_id].get("last_result", 0)
    
    msg = bot.send_message(
        message.chat.id,
        f"🔢 عدد را برای فاکتوریل وارد کنید (پیش‌فرض: {last_result}):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_factorial, user_id, last_result)

def process_factorial(message, user_id, default_value):
    try:
        text = message.text.strip()
        if text == "":
            value = default_value
        else:
            value = float(text.replace(',', '.'))
        
        if value.is_integer() and value >= 0:
            result = math.factorial(int(value))
            user_data[user_id]["last_result"] = result
            bot.send_message(
                message.chat.id,
                f"✅ **نتیجه:** `{result}`",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ فاکتوریل فقط برای اعداد صحیح مثبت تعریف می‌شود!")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "1/x")
def inverse_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    last_result = user_data[user_id].get("last_result", 0)
    
    msg = bot.send_message(
        message.chat.id,
        f"🔢 عدد را برای معکوس وارد کنید (پیش‌فرض: {last_result}):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_inverse, user_id, last_result)

def process_inverse(message, user_id, default_value):
    try:
        text = message.text.strip()
        if text == "":
            value = default_value
        else:
            value = float(text.replace(',', '.'))
        
        if value != 0:
            result = 1 / value
            user_data[user_id]["last_result"] = result
            bot.send_message(
                message.chat.id,
                f"✅ **نتیجه:** `{result}`",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ تقسیم بر صفر امکان‌پذیر نیست!")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "|x|")
def abs_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    last_result = user_data[user_id].get("last_result", 0)
    
    msg = bot.send_message(
        message.chat.id,
        f"🔢 عدد را برای قدر مطلق وارد کنید (پیش‌فرض: {last_result}):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_abs, user_id, last_result)

def process_abs(message, user_id, default_value):
    try:
        text = message.text.strip()
        if text == "":
            value = default_value
        else:
            value = float(text.replace(',', '.'))
        
        result = abs(value)
        user_data[user_id]["last_result"] = result
        bot.send_message(
            message.chat.id,
            f"✅ **نتیجه:** `{result}`",
            parse_mode="Markdown"
        )
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "exp")
def exp_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    last_result = user_data[user_id].get("last_result", 0)
    
    msg = bot.send_message(
        message.chat.id,
        f"🔢 عدد را برای e^x وارد کنید (پیش‌فرض: {last_result}):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_exp, user_id, last_result)

def process_exp(message, user_id, default_value):
    try:
        text = message.text.strip()
        if text == "":
            value = default_value
        else:
            value = float(text.replace(',', '.'))
        
        result = math.exp(value)
        user_data[user_id]["last_result"] = result
        bot.send_message(
            message.chat.id,
            f"✅ **نتیجه:** `{result}`",
            parse_mode="Markdown"
        )
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً یک عدد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text == "mod")
def mod_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    msg = bot.send_message(
        message.chat.id,
        "🔢 دو عدد را به فرم `a mod b` وارد کنید (مثال: 10 mod 3):",
        parse_mode="Markdown"
    )
    
    bot.register_next_step_handler(msg, process_mod, user_id)

def process_mod(message, user_id):
    try:
        text = message.text.strip()
        if 'mod' in text:
            parts = text.split('mod')
            a = float(parts[0].strip())
            b = float(parts[1].strip())
            
            if b == 0:
                bot.send_message(message.chat.id, "❌ تقسیم بر صفر امکان‌پذیر نیست!")
                return
            
            result = a % b
            user_data[user_id]["last_result"] = result
            bot.send_message(
                message.chat.id,
                f"✅ **نتیجه:** `{result}`",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ فرمت صحیح: a mod b")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ لطفاً اعداد معتبر وارد کنید!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطا: {str(e)[:50]}")

@bot.message_handler(func=lambda m: m.text in ["π", "e"])
def constant_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "standard"}
    
    if message.text == "π":
        result = math.pi
    else:
        result = math.e
    
    user_data[user_id]["last_result"] = result
    bot.send_message(
        message.chat.id,
        f"✅ **مقدار {message.text}:** `{result}`",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text in ["^2", "^3", "√"])
def power_root_handler(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
    
    if user_id in user_data:
        expr = user_data[user_id].get("expression", "")
        last_result = user_data[user_id].get("last_result", 0)
        
        if message.text == "^2":
            new_expr = expr + f"^{last_result}^2"
            user_data[user_id]["expression"] = new_expr
        elif message.text == "^3":
            new_expr = expr + f"^{last_result}^3"
            user_data[user_id]["expression"] = new_expr
        elif message.text == "√":
            new_expr = expr + f"sqrt({last_result})"
            user_data[user_id]["expression"] = new_expr
        
        current = user_data[user_id]["expression"] or "0"
        bot.send_message(
            message.chat.id,
            f"📝 **عبارت فعلی:** `{current}`\n🔢 برای محاسبه = را بزنید",
            parse_mode="Markdown"
        )
    else:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "scientific"}
        bot.send_message(message.chat.id, "⚠️ ابتدا یک عدد وارد کنید!")

@bot.message_handler(func=lambda m: m.text not in ["C", "=", "🗑 پاک کردن", "📊 راهنما", "📞 پشتیبانی", "🧮 ماشین حساب", "🔙 بازگشت", "sin", "cos", "tan", "log", "ln", "asin", "acos", "atan", "!", "1/x", "|x|", "exp", "mod", "π", "e", "^2", "^3", "√"])
def calculator_handler(message):
    user_id = message.from_user.id
    text = message.text
    
    if user_id not in user_data:
        user_data[user_id] = {"expression": "", "last_result": 0, "mode": "standard"}
    
    if text == "C":
        user_data[user_id]["expression"] = ""
        bot.send_message(message.chat.id, "✅ **پاک شد**", parse_mode="Markdown")
        return
    
    # اضافه کردن کاراکتر به عبارت
    current_expr = user_data[user_id].get("expression", "")
    
    if text == "=":
        if current_expr:
            success, result = calculate(current_expr)
            if success:
                user_data[user_id]["last_result"] = result
                user_data[user_id]["expression"] = str(result)
                bot.send_message(
                    message.chat.id,
                    f"✅ **نتیجه:** `{result}`",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(message.chat.id, result)  # result پیام خطاست
                user_data[user_id]["expression"] = ""
        else:
            bot.send_message(message.chat.id, "⚠️ هیچ عبارتی وارد نشده است!")
        return
    
    # تبدیل دکمه‌ها به کاراکترهای مناسب
    if text == "×":
        char = "*"
    elif text == "÷":
        char = "/"
    elif text == "√":
        char = "sqrt("
    elif text == "^":
        char = "**"
    elif text == "%":
        char = "%"
    elif text == "π":
        char = "pi"
    elif text == "e":
        char = "e"
    else:
        char = text
    
    user_data[user_id]["expression"] = current_expr + char
    current = user_data[user_id]["expression"] or "0"
    
    bot.send_message(
        message.chat.id,
        f"📝 **عبارت فعلی:** `{current}`\n🔢 برای محاسبه = را بزنید",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: True)
def default_handler(message):
    bot.reply_to(
        message,
        "❌ دستور نامعتبر!\nاز دکمه‌های ماشین حساب استفاده کنید."
    )

# ==================== اجرا ====================

if __name__ == "__main__":
    print("="*60)
    print("🧮 ربات ماشین حساب شیشه‌ای - Glass Calculator")
    print("="*60)
    print(f"👨‍💻 سازنده: @{DEVELOPER_USERNAME}")
    print(f"📢 کانال پشتیبانی: {SUPPORT_CHANNEL}")
    print(f"📌 آدرس بات: {BASE_URL}")
    print("="*60)
    
    # تنظیم webhook
    def run_setup():
        time.sleep(3)
        set_webhook()
    
    threading.Thread(target=run_setup, daemon=True).start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
