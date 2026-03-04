# Фулл будет в https://t.me/+SE7QaJWSNHZhZmIy
# Фулл будет в https://t.me/+SE7QaJWSNHZhZmIy
# Фулл будет в https://t.me/+SE7QaJWSNHZhZmIy
# Фулл будет в https://t.me/+SE7QaJWSNHZhZmIy
# Фулл будет в https://t.me/+SE7QaJWSNHZhZmIy


# СПАСИБО ТЕБЕ @attackcounte я ценю чем ты мне помог


import os
import sys
import logging
import asyncio
import sqlite3
import json
import aiohttp
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import ReportRequest
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import random

# Конфигурация
API_TOKEN = '8750370510:AAHQJJA4T-oBamoe3q5ud3ics0bR4vry_3Y' #токен бота
ADMINS = [7541535601] #айди админа если надо несколько вводите так: 11111, 22222
STICKER_ID = 'CAACAgIAAxkBAAEQF4ZoWn0zvZUi5kw-VabOdnoueLgoVAACX3gAAri60EqVi9ckQR15FTYE' #айди стикера можете заменить на свой
CRYPTOBOT_TOKEN = '520778:AApyiBBUzWu44k6pdc1WFee6d23nStw04DT' #криптотокен
LOG_CHANNEL_ID = -1003758856935 #айди канала
LOG_FILE_DIR = "logs"

REQUIRED_CHANNELS = [
    {"id": -1003749718223, "name": "Канал 1", "url": "https://t.me/nemezidapizza"} # в id ставьте айди для подписки а после url ссылка на канал
]

# Инициализация бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# База данных
conn = sqlite3.connect('plRML.db', check_same_thread=False)
cursor = conn.cursor()


if not os.path.exists(LOG_FILE_DIR):
    os.makedirs(LOG_FILE_DIR)

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    username TEXT,
    premium BOOLEAN DEFAULT 0,
    subscription_end DATETIME
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS promocodes (
    code TEXT PRIMARY KEY,
    activations INTEGER,
    days INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    currency TEXT,
    invoice_id TEXT,
    status TEXT DEFAULT 'pending',
    subscription_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

# Загрузка почтовых аккаунтов
EMAIL_ACCOUNTS = {}
try:
    sys.path.append(os.getcwd())
    from mail import EMAIL_ACCOUNTS as loaded_accounts
    EMAIL_ACCOUNTS = loaded_accounts
    logger.info(f"Loaded {len(EMAIL_ACCOUNTS)} email accounts")
except Exception as e:
    logger.error(f"Error loading email accounts: {e}")

# Загрузка сессий Telethon
def load_telethon_sessions():
    sessions = []
    session_dir = os.path.join(os.getcwd(), 'sessions')
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        return sessions
    
    for file in os.listdir(session_dir):
        if file.endswith('.session'):
            sessions.append(os.path.join(session_dir, file))
    
    logger.info(f"Loaded {len(sessions)} Telethon sessions")
    return sessions

TELEGRAM_SESSIONS = load_telethon_sessions()

# Состояния FSM
class Form(StatesGroup):
    promo_waiting = State()
    order_link = State()
    web_link = State()
    mail_link = State()
    admin_user_id = State()
    admin_action = State()
    admin_days = State()
    promo_create = State()
    promo_activations = State()
    promo_days = State()
    promo_delete = State()
    web_report_reason = State()
    mail_report_reason = State()
    admin_broadcast = State()
    premium_order_link = State()
    mail_subject = State()
    mail_text = State()

# Добавляем новые состояния для админ-панели
class AdminForm(StatesGroup):
    user_id = State()
    days = State()
    promo_code = State()
    promo_activations = State()
    promo_days = State()
    broadcast_message = State()

# =====================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================

def get_user_data(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

async def check_subscription(user_id):
    """Проверяет подписку пользователя на все требуемые каналы"""
    try:
        for channel in REQUIRED_CHANNELS:
            chat_member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

def subscription_required_keyboard():
    """Клавиатура с кнопками для подписки"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    for channel in REQUIRED_CHANNELS:
        keyboard.add(InlineKeyboardButton(f"[1️⃣]Подпишись", url=channel["url"]))
    keyboard.add(InlineKeyboardButton("[🔎Проверить]", callback_data="check_subscription"))
    return keyboard

def update_user_data(user_id, full_name, username):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
        (user_id, full_name, username)
    )
    cursor.execute(
        "UPDATE users SET full_name = ?, username = ? WHERE user_id = ?",
        (full_name, username, user_id)
    )
    conn.commit()

def is_premium_user(user_id):
    cursor.execute("SELECT premium FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def get_subscription_status(user_id):
    user = get_user_data(user_id)
    if user and user[4]:
        end_date = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
        return "Активна" if end_date > datetime.now() else "Истекла"
    return "Истекла"

def set_premium_status(user_id, premium_status):
    cursor.execute(
        "UPDATE users SET premium = ? WHERE user_id = ?",
        (premium_status, user_id)
    )
    conn.commit()

def is_subscription_active(user_id):
    user = get_user_data(user_id)
    if user and user[4]:
        end_date = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
        return end_date > datetime.now()
    return False

def add_subscription(user_id, days):
    user = get_user_data(user_id)
    if user and user[4]:
        current_end = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
        new_end = current_end + timedelta(days=days)
    else:
        new_end = datetime.now() + timedelta(days=days)
    
    cursor.execute(
        "UPDATE users SET subscription_end = ? WHERE user_id = ?",
        (new_end.strftime("%Y-%m-%d %H:%M:%S"), user_id)
    )
    conn.commit()

def create_payment(user_id, amount, currency, sub_type):
    cursor.execute(
        "INSERT INTO payments (user_id, amount, currency, subscription_type) VALUES (?, ?, ?, ?)",
        (user_id, amount, currency, sub_type)
    )
    conn.commit()
    return cursor.lastrowid

def get_payment(payment_id):
    cursor.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
    return cursor.fetchone()

def update_payment_invoice(payment_id, invoice_id):
    cursor.execute(
        "UPDATE payments SET invoice_id = ? WHERE payment_id = ?",
        (invoice_id, payment_id)
    )
    conn.commit()

def update_payment_status(payment_id, status):
    cursor.execute(
        "UPDATE payments SET status = ? WHERE payment_id = ?",
        (status, payment_id)
    )
    conn.commit()

def check_promo(code):
    cursor.execute("SELECT * FROM promocodes WHERE code = ?", (code,))
    return cursor.fetchone()

def use_promo(code):
    cursor.execute("SELECT activations FROM promocodes WHERE code = ?", (code,))
    result = cursor.fetchone()
    if not result:
        return False
    
    activations = result[0]
    if activations > 1:
        cursor.execute(
            "UPDATE promocodes SET activations = activations - 1 WHERE code = ?",
            (code,)
        )
    else:
        cursor.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    conn.commit()
    return True

def has_required_username(username):
    return username and "@NemezidaPh" in username

async def create_cryptobot_invoice(amount, currency, user_id):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "asset": currency,
        "amount": str(amount),
        "description": f"Подписка Nemezida RML для пользователя {user_id}",
        "hidden_message": "Оплата подписки Nemezida RML",
        "paid_btn_name": "viewItem",
        "paid_btn_url": "https://t.me/BRRMLBot",
        "payload": str(user_id),
        "allow_comments": False,
        "allow_anonymous": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok'):
                    return data['result']
            return None

def get_subscription_status(user_id):
    user = get_user_data(user_id)
    if user and user[4]:
        end_date = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
        return end_date.strftime("%d.%m.%Y %H:%M")  # Возвращаем дату вместо статуса
    return "Истекла"

async def check_cryptobot_invoice(invoice_id):
    url = f"https://pay.crypt.bot/api/getInvoices?invoice_ids={invoice_id}"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('ok') and data['result']['items']:
                    return data['result']['items'][0]['status']
            return None

async def send_admin_log(user_id, username, target_link, target_id, target_username,
                        success_count, failed_count, method, session_logs="", is_premium=False):
    """Отправляет стилизованный лог в канал с деталями по сессиям"""
    # Формируем имя файла лога
    log_filename = f"NemezidaRML_botnet_{random.randint(1000, 9999)}.txt"
    log_filepath = os.path.join(LOG_FILE_DIR, log_filename)

    # Формируем содержимое лога
    log_content = f"""NemezidaRML log | botnet-method
------------------------------------------
Пользователь: {user_id} (@{username})
Ссылка: {target_link}
------------------------------------------
{session_logs}
------------------------------------------
[TARGET]
ID: {target_id}
USERNAME: @{target_username}
------------------------------------------
Успешно: {success_count}
Неуспешно: {failed_count}
Флудов: 0
"""

    # Сохраняем полный лог в файл
    with open(log_filepath, 'w', encoding='utf-8') as f:
        f.write(log_content)

    # Формируем сообщение для канала
    message_text = f"""<b>
📈 Бот завершил работу
└─📂Метод: {method}-method

🎯 Таргет
└─ID: {target_id}
└─USERNAME: @{target_username}

🟢Успешно: {success_count}
🔴Неуспешно: {failed_count}

⛓️Ссылка: {target_link}
👤Пользователь: {user_id} (@{username})</b>"""

    # Отправляем сообщение в канал
    try:
        with open(log_filepath, 'rb') as log_file:
            await bot.send_document(
                chat_id=LOG_CHANNEL_ID,
                document=log_file,
                caption=message_text,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка отправки лога в канал: {e}")


async def send_telegram_report(session_file, chat_id, message_id):
    try:
        # Все возможные причины и их маппинг на option
        reasons = {
            'spam': '1',
            'violence': '2',
            'pornography': '3',
            'child_abuse': '4',
            'illegal_drugs': '5',
            'personal_details': '6',
            'copyright': '7',
            'other': '8'
        }

        # Выбираем случайную причину
        reason, option = random.choice(list(reasons.items()))

        async with TelegramClient(session_file, 111111, '111111') as client: #замените на свои апи айди и апи хесш
            if not await client.is_user_authorized():
                logger.error(f"Сессия {session_file} не авторизована!")
                return False

            try:
                peer = await client.get_input_entity(chat_id)
            except Exception as e:
                logger.error(f"Ошибка получения чата {chat_id}: {e}")
                return False

            logger.info(f"Отправка жалобы: chat={chat_id}, msg={message_id}, option={option}")

            await client(ReportRequest(
                peer=peer,
                id=[int(message_id)],
                option=option,
                message="Нарушение правил платформы"
            ))
            return True

    except Exception as e:
        logger.error(f"Ошибка при отправке жалобы через {session_file}: {str(e)}")
        return False


async def get_target_info(chat_id, message_id):
    """Получает информацию о цели (ID и username)"""
    try:
        # Используем первую доступную сессию для получения информации
        if not TELEGRAM_SESSIONS:
            return "unknown", "unknown"

        async with TelegramClient(TELEGRAM_SESSIONS[0], 111111, '111111') as client: #замените на свои апи айди и апи хесш
            if not await client.is_user_authorized():
                return "unknown", "unknown"

            try:
                msg = await client.get_messages(int(chat_id) if chat_id.isdigit() else chat_id, ids=int(message_id))
                if msg and msg.sender:
                    target_entity = await client.get_entity(msg.sender)
                    target_id = target_entity.id
                    target_username = getattr(target_entity, 'username', 'unknown')
                    return target_id, target_username
            except Exception as e:
                logger.error(f"Error getting target info: {e}")
                return "unknown", "unknown"
    except Exception as e:
        logger.error(f"Error creating client for target info: {e}")
        return "unknown", "unknown"


async def send_web_report(chat_id, message_id, reason):
    url = "https://telegram.org/support"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reason": reason,
        "description": "Нарушение правил платформы"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as response:
            return response.status == 200

async def send_email_report(email, password, report_data):
    try:
        msg = MIMEText(
            f"Жалоба на сообщение в Telegram\n\n"
            f"Чат: {report_data['chat_id']}\n"
            f"Сообщение: {report_data['message_id']}\n"
            f"Причина: {report_data['reason']}\n\n"
            f"Описание: Нарушение правил платформы"
        )
        msg['Subject'] = 'Жалоба на сообщение в Telegram'
        msg['From'] = email
        msg['To'] = 'abuse@telegram.org'
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(email, password)
            server.send_message(msg)
            return True
    except Exception as e:
        logger.error(f"Error sending email from {email}: {e}")
        return False

# =====================
# КЛАВИАТУРЫ
# =====================

def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🍕 Заказать пиццу", callback_data="order_RML")
    )
    keyboard.row(
        InlineKeyboardButton("❓ Информация", callback_data="info"),
        InlineKeyboardButton("📕 Профиль", callback_data="profile")
    )
    keyboard.row(
        InlineKeyboardButton("🛍️ Цены на пиццу", callback_data="prices"),
        InlineKeyboardButton("🎁 Промокод", callback_data="promo")
    )
    return keyboard

def info_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔥 Канал", url="https://t.me/+SE7QaJWSNHZhZmIy"))
    keyboard.add(InlineKeyboardButton("💬 Наш чат", url="https://t.me/ubischat"))
    keyboard.add(InlineKeyboardButton("🎱 Администрация", url="https://t.me/antarcticubis"))
    keyboard.add(InlineKeyboardButton("📄 Мануал", url="https://teletype.in/@NemezidaRML/NemezidaRMLmanuals"))
    keyboard.add(InlineKeyboardButton("👥 Поддержка", url="https://t.me/antarcticubis"))
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="main_menu"))
    return keyboard

def back_to_main_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="main_menu"))
    return keyboard

def prices_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        InlineKeyboardButton("⚡ 1 День - 2$", callback_data="buy_1"),
        InlineKeyboardButton("⚡ 3 Дня - 3$", callback_data="buy_3")
    )
    keyboard.row(
        InlineKeyboardButton("⚡ 7 Дней - 5$", callback_data="buy_7"),
        InlineKeyboardButton("⚡ 30 Дней - 9$", callback_data="buy_30")
    )
    keyboard.add(InlineKeyboardButton("⚡ Навсегда - 16$", callback_data="buy_forever"))
    keyboard.add(InlineKeyboardButton("⚡ Premium Upgrade [-40%]", callback_data="buy_premium"))
    keyboard.row(
        InlineKeyboardButton("💳 Оплата картой", callback_data="card_payment"),
        InlineKeyboardButton("👑 Что такое премиум?", callback_data="premium_info")
    )
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="main_menu"))
    return keyboard

def payment_keyboard(payment_id, invoice_url=None):
    keyboard = InlineKeyboardMarkup()
    if invoice_url:
        keyboard.add(InlineKeyboardButton("💸 Оплатить", url=invoice_url))
    keyboard.add(InlineKeyboardButton("🔍 Проверить", callback_data=f"check_{payment_id}"))
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="prices"))
    return keyboard

def order_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🤖 Обычная пицца", callback_data="order_normal"))
    keyboard.row(
        InlineKeyboardButton("🌐 Веб пицца", callback_data="order_web"),
        InlineKeyboardButton("✉️ Почтовая пицца", callback_data="order_mail")
    )
    keyboard.add(InlineKeyboardButton("👑 Премиальная пицца", callback_data="order_premium"))
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="main_menu"))
    return keyboard

def admin_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("👤 Управление подписками", callback_data="admin_subscriptions"))
    keyboard.add(InlineKeyboardButton("🎫 Управление промокодами", callback_data="admin_promocodes"))
    keyboard.add(InlineKeyboardButton("📢 Рассылка сообщений", callback_data="admin_broadcast"))
    keyboard.add(InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu"))
    return keyboard

def subscription_management_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("➕ Выдать подписку", callback_data="admin_give_sub"))
    keyboard.add(InlineKeyboardButton("➖ Забрать подписку", callback_data="admin_revoke_sub"))
    keyboard.add(InlineKeyboardButton("👑 Выдать премиум", callback_data="admin_give_premium"))
    keyboard.add(InlineKeyboardButton("🚫 Забрать премиум", callback_data="admin_revoke_premium"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_menu"))

def promocode_management_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("➕ Создать промокод", callback_data="admin_create_promo"))
    keyboard.add(InlineKeyboardButton("➖ Удалить промокод", callback_data="admin_delete_promo"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_menu"))
    return keyboard

def broadcast_keyboard(url=None):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔻Прочитано", callback_data="broadcast_read")
    )
    keyboard.add(
        InlineKeyboardButton("🔥Подпишись", url=url if url else "https://t.me/+SE7QaJWSNHZhZmIy")
    )
    return keyboard

def report_reasons_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    reasons = [
        "child_abuse", "copyright", "fake", "geo political",
        "illegal_drugs", "personal_details", "pornography",
        "spam", "violence", "other"
    ]
    buttons = []
    for reason in reasons:
        buttons.append(InlineKeyboardButton(reason, callback_data=f"reason_{reason}"))
    
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("[🔙] Назад", callback_data="main_menu"))
    return keyboard

# =====================
# ОБРАБОТЧИКИ КОМАНД
# =====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await bot.send_sticker(message.chat.id, sticker=STICKER_ID)
    
    user = message.from_user
    update_user_data(user.id, user.full_name, user.username)
    
    try:
        photo = InputFile("nemezida.png")
        caption = "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>"
        
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        await message.answer(
            "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        return
    
    await message.answer(
        "⚙️ <b>Административная панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

# =====================
# ОБРАБОТЧИКИ CALLBACK
# =====================

@dp.callback_query_handler(lambda c: c.data == 'main_menu')
async def main_menu(callback_query: types.CallbackQuery):
    try:
        photo = InputFile("brRML.png")
        caption = "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>"
        
        await bot.edit_message_media(
            media=types.InputMediaPhoto(
                media=photo,
                caption=caption,
                parse_mode="HTML"
            ),
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=main_menu_keyboard()
        )
    except:
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == 'check_subscription')
async def check_subscription_callback(callback_query: types.CallbackQuery):
    if await check_subscription(callback_query.from_user.id):
        await callback_query.answer("✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.")
        try:
            photo = InputFile("brRML.png")
            caption = "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>"

            await bot.edit_message_media(
                media=types.InputMediaPhoto(
                    media=photo,
                    caption=caption,
                    parse_mode="HTML"
                ),
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=main_menu_keyboard()
            )
        except:
            await bot.edit_message_caption(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                caption="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
    else:
        await callback_query.answer("❌ Вы не подписаны на все каналы!", show_alert=True)


# Модифицируем все обработчики кнопок, добавляя проверку подписки
async def check_subscription_wrapper(callback_query: types.CallbackQuery, handler):
    if not await check_subscription(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="Для использования бота необходимо подписаться на наши каналы:",
            reply_markup=subscription_required_keyboard()
        )
        await callback_query.answer()
        return False
    return True

@dp.callback_query_handler(lambda c: c.data == 'info')
async def info_menu(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    caption = "<blockquote><b>Информация</b></blockquote>"
    
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=info_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == 'profile')
async def profile_menu(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    user = get_user_data(callback_query.from_user.id)

    # Получаем дату окончания подписки
    subscription_end = "Истекла"
    if user and user[4]:
        end_date = datetime.strptime(user[4], "%Y-%m-%d %H:%M:%S")
        subscription_end = end_date.strftime("%d.%m.%Y %H:%M")

    caption = f"""
<b>🍕 Профиль

▪️ Имя: {user[1]}
▪️ ID: {user[0]}
▪️ Username: @{user[2] if user[2] else 'N/A'}
▪️ Премиум: {'Есть' if user[3] else 'Нет'}

⏳Подписка: {subscription_end}</b>
"""
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'prices')
async def prices_menu(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    caption = """
<b>🍕 Ассортимент

<blockquote>🍕 Пицца:
└─ 1 день - 2$
└─ 3 дня - 3$
└─ 7 дней - 5$
└─ 30 дней - 9$
└─ Навсегда - 16$ 

👑 Премиум пицца:
└─ Навсегда - 7$ [-40%]</blockquote></b>
"""
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=prices_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('buy_'))
async def buy_menu(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    user_id = callback_query.from_user.id
    plan = callback_query.data.split('_')[1]

    plans = {
        '1': {'name': '1 день', 'amount': 2, 'type': '1 день', 'currency': 'USDT'},
        '3': {'name': '3 дня', 'amount': 3, 'type': '3 дня', 'currency': 'USDT'},
        '7': {'name': '7 дней', 'amount': 5, 'type': '7 дней', 'currency': 'USDT'},
        '30': {'name': '30 дней', 'amount': 9, 'type': '30 дней', 'currency': 'USDT'},
        'forever': {'name': 'Пицца навсегда', 'amount': 16, 'type': 'Навсегда', 'currency': 'USDT'},
        'premium': {'name': 'Премиум Пицца', 'amount': 7, 'type': 'Premium', 'currency': 'USDT'}
    }

    selected = plans[plan]
    payment_id = create_payment(user_id, selected['amount'], selected['currency'], selected['type'])

    # Создаем счет в CryptoBot
    invoice = await create_cryptobot_invoice(
        selected['amount'],
        selected['currency'],
        user_id
    )

    if not invoice:
        await callback_query.answer("Ошибка создания счета. Попробуйте позже.", show_alert=True)
        return

    update_payment_invoice(payment_id, invoice['invoice_id'])

    caption = f"""
<b><blockquote>🍕 Покупка пиццы</blockquote>
└─ Вы покупаете: 🍕 {selected['name']}
└─ Вы платите: {selected['amount']} {selected['currency']}</b>
"""
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=payment_keyboard(payment_id, invoice['pay_url']),
        parse_mode="HTML"
    )
    await callback_query.answer()

# Обновляем проверку платежа для премиума
@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def check_payment(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    payment_id = callback_query.data.split('_')[1]
    payment = get_payment(payment_id)
    
    if not payment:
        await callback_query.answer("Платеж не найден", show_alert=True)
        return
    
    # Проверяем статус в CryptoBot
    invoice_status = await check_cryptobot_invoice(payment[5])
    
    if not invoice_status:
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Ошибка проверки платежа!</b>",
            parse_mode="HTML"
        )
        await callback_query.answer()
        return
    
    if invoice_status == 'paid':
        days_map = {
            '1 день': 1,
            '3 дня': 3,
            '7 дней': 7,
            '30 дней': 30,
            'Навсегда': 36500,
            'Premium': 0
        }
        
        if payment[6] == 'Premium':
            cursor.execute(
                "UPDATE users SET premium = 1 WHERE user_id = ?",
                (payment[1],)
            )
            conn.commit()
        else:
            add_subscription(payment[1], days_map[payment[6]])
        
        update_payment_status(payment_id, 'paid')
        
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>✅ Оплата получена! Подписка активирована.</b>",
            parse_mode="HTML"
        )
    else:
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption=f"<b>❌ Оплата не получена! Статус: {invoice_status}</b>",
            parse_mode="HTML"
        )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'card_payment')
async def card_payment(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    caption = """
<b>🟢 Оплата по карте (ручная проверка)

<blockquote>🍕 Пицца:
└─ 1 день - 160р
└─ 3 дня - 250р
└─ 7 дней - 400р
└─ 30 дней -800р
└─ Навсегда - 500р [-60%]

👑 Премиум пицца:
└─ Навсегда - 600р [-40%]</blockquote>

🟢 Реквизиты: 1111111111111111(сбер)
💬 Комментарий: 7718262680, претензий не имею (обязательно)

🤝 После оплаты отправьте чек и напишите + в личные сообщения @antarcticubis</b>
"""
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'premium_info')
async def premium_info(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    caption = """
<b>👑 Премиум пицца

<blockquote>🔓 Премиум пицца даст:
└─ почты
└─ веб
└─ Прем отправку
└─ Преф в нашем чате</blockquote>

‼️Премиум пицца покупается как ДОПОЛНЕНИЕ к вашей активной пицце ‼️</b>
"""
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=back_to_main_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'promo')
async def promo_menu(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    
 

@dp.message_handler(state=Form.promo_waiting)
async def process_promo(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    promo = check_promo(code)
    
    if promo:
        add_subscription(message.from_user.id, promo[2])
        use_promo(code)
        response = "<b>✅ Промокод активирован! Подписка продлена.</b>"
    else:
        response = "<b>❌ Промокод не найден!</b>"
    
    await state.finish()
    await message.answer(response, parse_mode="HTML")
    
    # Возвращаем главное меню
    try:
        photo = InputFile("brRML.png")
        caption = "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>"
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except:
        await message.answer(
            "<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

@dp.callback_query_handler(lambda c: c.data == 'order_RML')
async def order_RML(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    caption = "<b>🍕 Заказ пиццы\n<blockquote>Посмотрите Мануал</blockquote></b>"

    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=caption,
        reply_markup=order_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'order_normal')
async def order_normal(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    if not is_subscription_active(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Ваша пицца истекла!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    await Form.order_link.set()
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption="""
<b>Отправьте ссылку на сообщение в формате:
https://t.me/username/123</b>
""",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler(state=Form.order_link)
async def process_normal_order_link(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split('/')
        chat_id = parts[-2]
        message_id = parts[-1]

        # Получаем информацию о цели
        target_id, target_username = await get_target_info(chat_id, message_id)

        await state.update_data(chat_id=chat_id, message_id=message_id)
        await message.answer("<b>📤 Запустил отправку пиццы...</b>", parse_mode="HTML")

        # Используем до 200 случайных сессий
        max_sessions = min(200, len(TELEGRAM_SESSIONS))
        selected_sessions = random.sample(TELEGRAM_SESSIONS, max_sessions) if len(TELEGRAM_SESSIONS) > 200 else TELEGRAM_SESSIONS

        log_filename = f"NemezidaRML_botnet_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        log_filepath = os.path.join(LOG_FILE_DIR, log_filename)

        log_content = f"""NemezidaRML log | botnet-method
------------------------------------------
Пользователь: {message.from_user.id} (@{message.from_user.username})
Ссылка: https://t.me/{chat_id}/{message_id}
------------------------------------------
"""
        session_logs = ""
        success_count = 0
        failed_count = 0

        for session in selected_sessions:
            session_name = os.path.basename(session)
            timestamp = datetime.now().strftime('[%H:%M:%S]')

            try:
                result = await send_telegram_report(session, chat_id, message_id)
                status = "[ДОСТАВЛЕНО]" if result else "[НЕВАЛИД]"
                session_logs += f"{timestamp} {session_name} -> https://t.me/{chat_id}/{message_id} - {status}\n"

                if result:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                error_msg = str(e)[:50]
                session_logs += f"{timestamp} {session_name} -> https://t.me/{chat_id}/{message_id} - [ОШИБКА: {error_msg}]\n"
                failed_count += 1

            await asyncio.sleep(random.uniform(0.5, 1.5))

        log_content += f"""
{session_logs}
------------------------------------------
[TARGET]
ID: {target_id}
USERNAME: @{target_username}
------------------------------------------
Успешно: {success_count}
Неуспешно: {failed_count}
Флудов: 0
"""

        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write(log_content)

        await send_admin_log(
            user_id=message.from_user.id,
            username=message.from_user.username,
            target_link=f"https://t.me/{chat_id}/{message_id}",
            target_id=target_id,
            target_username=target_username,
            success_count=success_count,
            failed_count=failed_count,
            method="обычная",
            session_logs=session_logs,
            is_premium=False
        )

        await bot.send_document(
            chat_id=message.chat.id,
            document=InputFile(log_filepath),
            caption=f""" <b>
🍕 Пицца доставлена!
└─📂 Пицца: обычная

🟢 Успешно отправлено: {success_count}
🔴 Не удалось отправить: {failed_count}
</b>""",
            parse_mode="HTML"
        )

        await state.finish()

        # Возвращаем главное меню
        try:
            photo = InputFile("brRML.png")
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            await bot.send_message(
                chat_id=message.chat.id,
                text="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )

    except Exception as e:
        await message.answer("<b>❌ Неверный формат ссылки. Пример: https://t.me/ubischat/10342</b>", parse_mode="HTML")
        logger.error(f"Ошибка обработки ссылки: {e}")


@dp.callback_query_handler(lambda c: c.data == 'order_web')
async def order_web(callback_query: types.CallbackQuery):
    if not await check_subscription_wrapper(callback_query, order_RML):
        return

    if not is_subscription_active(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Ваша пицца истекла!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    if not is_premium_user(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Веб-пицца доступна только для премиум пользователей!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    await Form.web_link.set()
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption="<b>✉️ Введите текст, который нужно отправить:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.message_handler(state=Form.web_link)
async def process_web_order_link(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(text=text)

    # Удаляем предыдущее сообщение "Запустил отправку пиццы..."
    try:
        await bot.delete_message(
            chat_id=message.chat.id,
            message_id=message.message_id - 1
        )
    except Exception as e:
        logger.error(f"Не удалось удалить предыдущее сообщение: {e}")

    # Отправляем одно сообщение о начале процесса
    processing_msg = await message.answer("<b>🔁Пицца скоро будет... Это может занять некоторое время.</b>", parse_mode="HTML")

    # Создаем лог файл
    log_filename = f"NemezidaRML_web_log_{random.randint(1000, 9999)}.txt"
    log_filepath = os.path.join(LOG_FILE_DIR, log_filename)

    # Формируем содержимое лога
    log_content = f"""NemezidaRML log | web-method
------------------------------------------
Пользователь: {message.from_user.id} (@{message.from_user.username})
Текст: {text}
------------------------------------------
"""

    success_count = 0
    failed_count = 0

    # Реальные запросы к веб-форме Telegram
    url = "https://telegram.org/support"
    payload = {
        "message": text,
        "email": f"{random.randint(100000, 999999)}@gmail.com",
        "setln": "ru"
    }

    for i in range(1, 201):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload) as response:
                    if response.status == 200:
                        status = "ДОШЛА ✅"
                        success_count += 1
                    else:
                        status = "НЕ ДОШЛА ❌"
                        failed_count += 1
        except Exception as e:
            status = f"ОШИБКА: {str(e)[:50]}"
            failed_count += 1

        timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
        log_content += f"{timestamp} Жалоба #{i} — {status}\n"
        await asyncio.sleep(0.1)  # Задержка между запросами

    log_content += f"""------------------------------------------
Успешно: {success_count}
Неуспешно: {failed_count}"""

    # Сохраняем лог
    with open(log_filepath, 'w', encoding='utf-8') as f:
        f.write(log_content)

    # Удаляем сообщение о процессе отправки
    try:
        await bot.delete_message(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
    except Exception as e:
        logger.error(f"Не удалось удалить сообщение о процессе: {e}")

    # Отправляем результат пользователю
    await bot.send_document(
        chat_id=message.chat.id,
        document=InputFile(log_filepath),
        caption=f"""<b>
🍕 Веб-пицца доставлена!

🟢 Успешно отправлено: {success_count}
🔴 Не удалось отправить: {failed_count}</b>""",
        parse_mode="HTML"
    )

    # Отправляем лог в канал
    await send_admin_log(
        user_id=message.from_user.id,
        username=message.from_user.username,
        target_link=text,
        target_id="N/A",
        target_username="N/A",
        success_count=success_count,
        failed_count=failed_count,
        method="web",
        session_logs=log_content
    )

    await state.finish()
    await show_main_menu(message.chat.id)


@dp.callback_query_handler(lambda c: c.data == 'order_mail')
async def order_mail(callback_query: types.CallbackQuery):
    if not is_subscription_active(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Ваша пицца истекла!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    if not is_premium_user(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Почтовая пицца доступна только для премиум пользователей!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    await Form.mail_subject.set()
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption="<b>✉️ Почтовая пицца\n└─ Введите тему письма:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.message_handler(state=Form.mail_subject)
async def process_mail_subject(message: types.Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await Form.mail_text.set()
    await message.answer("<b>✉️ Теперь введите текст пиццы:</b>", parse_mode="HTML")


@dp.message_handler(state=Form.mail_text)
async def process_mail_text(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    subject = state_data.get('subject')
    text = message.text

    await message.answer("<b>📤 Начинаю отправку пиццы...</b>", parse_mode="HTML")

    # Создаем лог файл
    log_filename = f"NemezidaRML_mail_log_{random.randint(1000, 9999)}.txt"
    log_filepath = os.path.join(LOG_FILE_DIR, log_filename)

    log_content = f"""NemezidaRML Mail-method | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
------------------------------------------
Пользователь: {message.from_user.id} (@{message.from_user.username})
Тема: {subject}
Текст: {text}
------------------------------------------
"""

    success_count = 0
    failed_count = 0

    # Список почтовых адресов Telegram для отправки
    telegram_emails = [
        'abuse@telegram.org',
        'dmca@telegram.org',
        'stopCA@telegram.org',
        'support@telegram.org'
    ]

    for email_acc, password in EMAIL_ACCOUNTS.items():
        timestamp = datetime.now().strftime('[%H:%M:%S]')

        # Формируем скрытый email для логов (первые 2 буквы + **** + @domain)
        hidden_email = f"{email_acc[:2]}****@{email_acc.split('@')[1]}"

        # Отправляем на каждый адрес Telegram
        for target_email in telegram_emails:
            try:
                msg = MIMEText(text)
                msg['Subject'] = subject
                msg['From'] = email_acc
                msg['To'] = target_email

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(email_acc, password)
                    server.send_message(msg)

                log_content += f"{timestamp} {hidden_email} -> {target_email} [ДОСТАВЛЕНО]\n"
                success_count += 1
            except Exception as e:
                error_msg = str(e)[:50]
                log_content += f"{timestamp} {hidden_email} -> {target_email} [НЕ ДОСТАВЛЕНО] {error_msg}\n"
                failed_count += 1

            await asyncio.sleep(1)  # Задержка между отправками

    log_content += f"""------------------------------------------
Итог:
Успешно: {success_count}
Неуспешно: {failed_count}
"""

    # Сохраняем лог
    with open(log_filepath, 'w', encoding='utf-8') as f:
        f.write(log_content)

    # Отправляем результат пользователю
    await bot.send_document(
        chat_id=message.chat.id,
        document=InputFile(log_filepath),
        caption=f"""<b>🍕 Пицца доставлена
└─ Пицца: почты 

🟢 Успешно отправлено: {success_count}
🔴 Не удалось отправить: {failed_count}</b>""",
        parse_mode="HTML"
    )

    # Отправляем лог в канал
    await send_admin_log(
        user_id=message.from_user.id,
        username=message.from_user.username,
        target_link=f"Тема: {subject}",
        target_id="N/A",
        target_username="N/A",
        success_count=success_count,
        failed_count=failed_count,
        method="почты (все адреса)",
        session_logs=log_content
    )

    await state.finish()
    await show_main_menu(message.chat.id)


@dp.callback_query_handler(lambda c: c.data == 'order_premium')
async def order_premium(callback_query: types.CallbackQuery):
    if not is_subscription_active(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Ваша пицца истекла!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    if not is_premium_user(callback_query.from_user.id):
        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption="<b>❌ Премиум пицца доступна только для премиум пользователей!</b>",
            reply_markup=back_to_main_keyboard(),
            parse_mode="HTML"
        )
        return

    await Form.premium_order_link.set()
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption="""
<b>👑 Отправьте ссылку на сообщение в формате:
https://t.me/username/123</b>""",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler(state=Form.premium_order_link)
async def process_premium_order_link(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split('/')
        chat_id = parts[-2]
        message_id = parts[-1]

        # Получаем информацию о цели
        target_id, target_username = await get_target_info(chat_id, message_id)

        await state.update_data(chat_id=chat_id, message_id=message_id)
        await message.answer("<b>👑 Запустил отправку пиццы...</b>", parse_mode="HTML")

        # Используем до 500 сессий для премиум-заказа
        max_sessions = min(500, len(TELEGRAM_SESSIONS))
        selected_sessions = random.sample(TELEGRAM_SESSIONS, max_sessions) if len(TELEGRAM_SESSIONS) > 500 else TELEGRAM_SESSIONS

        log_filename = f"premium_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        log_filepath = os.path.join(LOG_FILE_DIR, log_filename)

        log_content = f"""NemezidaRML Premium log | fast-method
------------------------------------------
Пользователь: {message.from_user.id} (@{message.from_user.username})
Ссылка: https://t.me/{chat_id}/{message_id}
------------------------------------------
"""
        session_logs = ""
        success_count = 0
        failed_count = 0

        for session in selected_sessions:
            session_name = os.path.basename(session)
            timestamp = datetime.now().strftime('[%H:%M:%S]')

            try:
                result = await send_telegram_report(session, chat_id, message_id)
                status = "[ДОСТАВЛЕНО]" if result else "[НЕВАЛИД]"
                session_logs += f"{timestamp} {session_name} -> https://t.me/{chat_id}/{message_id} - {status}\n"

                if result:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                error_msg = str(e)[:50]
                session_logs += f"{timestamp} {session_name} -> https://t.me/{chat_id}/{message_id} - [ОШИБКА: {error_msg}]\n"
                failed_count += 1

            await asyncio.sleep(random.uniform(0.2, 0.8))  # Меньшая задержка для премиум

        log_content += session_logs
        log_content += f"""------------------------------------------
[TARGET]
ID: {target_id}
USERNAME: @{target_username}
------------------------------------------
Успешно: {success_count}
Неуспешно: {failed_count}
Флудов: 0
"""

        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write(log_content)

        await send_admin_log(
            user_id=message.from_user.id,
            username=message.from_user.username,
            target_link=f"https://t.me/{chat_id}/{message_id}",
            target_id=target_id,
            target_username=target_username,
            success_count=success_count,
            failed_count=failed_count,
            method="Премиум",
            session_logs=session_logs,
            is_premium=True
        )

        await bot.send_document(
            chat_id=message.chat.id,
            document=InputFile(log_filepath),
            caption=f"""<b>
🍕 Премиум пицца доставлена!
└─📂 Метод: Крутая пицца

🟢 Успешно отправлено: {success_count}
🔴 Не удалось отправить: {failed_count}
</b>""",
            parse_mode="HTML"
        )

        await state.finish()
        await show_main_menu(message.chat.id)

    except Exception as e:
        logger.error(f"Ошибка обработки премиум заказа: {e}")
        await message.answer("<b>❌ Неверный формат ссылки. Пример: https://t.me/ubischat/10342</b>", parse_mode="HTML")

async def show_main_menu(chat_id):
    try:
        photo = InputFile("brRML.png")
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        await bot.send_message(
            chat_id=chat_id,
            text="<blockquote><b>🍕 Хочешь горячей пиццы? Добро пожаловать в Nemezida RML!</b></blockquote>",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )

# =====================
# АДМИН ПАНЕЛЬ
# =====================

@dp.callback_query_handler(lambda c: c.data == 'admin_menu')
async def admin_menu(callback_query: types.CallbackQuery):
    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption="⚙️ <b>Административная панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == 'admin_subscriptions')
async def admin_subscriptions(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("➕ Выдать подписку", callback_data="admin_give_sub"))
    keyboard.add(InlineKeyboardButton("➖ Забрать подписку", callback_data="admin_revoke_sub"))
    keyboard.add(InlineKeyboardButton("👑 Выдать премиум", callback_data="admin_give_premium"))
    keyboard.add(InlineKeyboardButton("🚫 Забрать премиум", callback_data="admin_revoke_premium"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_menu"))

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="⚙️ <b>Управление подписками</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_promocodes')
async def admin_promocodes(callback_query: types.CallbackQuery):
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="⚙️ <b>Управление промокодами</b>",
        reply_markup=promocode_management_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_give_sub')
async def admin_give_sub(callback_query: types.CallbackQuery):
    await Form.admin_user_id.set()
    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data(action='give')
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="👤 <b>Введите ID пользователя:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'admin_revoke_sub')
async def admin_revoke_sub(callback_query: types.CallbackQuery):
    await Form.admin_user_id.set()
    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data(action='revoke')
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="👤 <b>Введите ID пользователя:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler(state=Form.admin_user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID:")
        return
    
    state_data = await state.get_data()
    action = state_data.get('action')
    
    if action == 'give':
        await Form.admin_days.set()
        await state.update_data(user_id=user_id)
        await message.answer("📅 <b>Введите количество дней:</b>", parse_mode="HTML")
    elif action == 'revoke':
        cursor.execute(
            "UPDATE users SET subscription_end = NULL WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        await state.finish()
        await message.answer(f"✅ Подписка пользователя {user_id} отозвана!")
        
        # Возврат в админ-панель
        await message.answer(
            "⚙️ <b>Административная панель</b>",
            reply_markup=admin_keyboard(),
            parse_mode="HTML"
        )

@dp.message_handler(state=Form.admin_days)
async def process_admin_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число дней:")
        return
    
    state_data = await state.get_data()
    user_id = state_data.get('user_id')
    
    add_subscription(user_id, days)
    await state.finish()
    await message.answer(f"✅ Пользователю {user_id} выдана подписка на {days} дней!")
    
    # Возврат в админ-панель
    await message.answer(
        "⚙️ <b>Административная панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_create_promo')
async def admin_create_promo(callback_query: types.CallbackQuery):
    await Form.promo_create.set()
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="🎫 <b>Введите промокод:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler(state=Form.promo_create)
async def process_promo_create(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if check_promo(code):
        await message.answer("❌ Этот промокод уже существует. Введите другой:")
        return
    
    await state.update_data(code=code)
    await Form.promo_activations.set()
    await message.answer("🔢 <b>Введите количество активаций:</b>", parse_mode="HTML")

@dp.message_handler(state=Form.promo_activations)
async def process_promo_activations(message: types.Message, state: FSMContext):
    try:
        activations = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число:")
        return
    
    await state.update_data(activations=activations)
    await Form.promo_days.set()
    await message.answer("📅 <b>Введите количество дней подписки:</b>", parse_mode="HTML")

@dp.message_handler(state=Form.promo_days)
async def process_promo_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число дней:")
        return
    
    state_data = await state.get_data()
    code = state_data.get('code')
    activations = state_data.get('activations')
    
    cursor.execute(
        "INSERT INTO promocodes (code, activations, days) VALUES (?, ?, ?)",
        (code, activations, days)
    )
    conn.commit()
    
    await state.finish()
    await message.answer(f"✅ Промокод {code} создан!")
    
    # Возврат в админ-панель
    await message.answer(
        "⚙️ <b>Административная панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: c.data == 'admin_delete_promo')
async def admin_delete_promo(callback_query: types.CallbackQuery):
    await Form.promo_delete.set()
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="🎫 <b>Введите промокод для удаления:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()

@dp.message_handler(state=Form.promo_delete)
async def process_promo_delete(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    promo = check_promo(code)
    
    if not promo:
        await message.answer("❌ Промокод не найден. Введите существующий промокод:")
        return
    
    cursor.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    conn.commit()
    
    await state.finish()
    await message.answer(f"✅ Промокод {code} удален!")
    
    # Возврат в админ-панель
    await message.answer(
        "⚙️ <b>Административная панель</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query_handler(lambda c: c.data == 'admin_give_premium')
async def admin_give_premium(callback_query: types.CallbackQuery):
    await AdminForm.user_id.set()
    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data(action='give_premium')

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="👤 <b>Введите ID пользователя для выдачи премиума:</b>\n\nПример: 123456789",
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == 'admin_revoke_premium')
async def admin_revoke_premium(callback_query: types.CallbackQuery):
    await Form.admin_user_id.set()
    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data(action='revoke_premium')

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="👤 <b>Введите ID пользователя для отзыва премиума:</b>",
        parse_mode="HTML"
    )
    await callback_query.answer()


# Модифицируем обработчик ввода ID пользователя
@dp.message_handler(state=AdminForm.user_id)
async def process_admin_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        state_data = await state.get_data()
        action = state_data.get('action')

        if action == 'give_premium':
            set_premium_status(user_id, 1)
            await state.finish()
            await message.answer(f"✅ Пользователю {user_id} успешно выдан премиум-статус!")
            await show_admin_menu(message)
        elif action == 'revoke_premium':
            set_premium_status(user_id, 0)
            await state.finish()
            await message.answer(f"✅ У пользователя {user_id} успешно отозван премиум-статус!")
            await show_admin_menu(message)
        elif action == 'give_sub':
            await AdminForm.days.set()
            await state.update_data(user_id=user_id)
            await message.answer("📅 <b>Введите количество дней подписки:</b>\n\nПример: 30", parse_mode="HTML")
        elif action == 'revoke_sub':
            cursor.execute("UPDATE users SET subscription_end = NULL WHERE user_id = ?", (user_id,))
            conn.commit()
            await state.finish()
            await message.answer(f"✅ Подписка пользователя {user_id} успешно отозвана!")
            await show_admin_menu(message)

    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя:")
    except Exception as e:
        logger.error(f"Ошибка обработки ID пользователя: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте еще раз.")
        await state.finish()
        await show_admin_menu(message)


@dp.callback_query_handler(lambda c: c.data == 'admin_broadcast')
async def admin_broadcast_start(callback_query: types.CallbackQuery):
    await Form.admin_broadcast.set()
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="📢 <b>Введите текст для рассылки:</b>\n\nМожно добавить URL для кнопки 'Подпишись' в конце сообщения, отделив его символом '|'",
        parse_mode="HTML"
    )
    await callback_query.answer()


# Обработчик текста рассылки
@dp.message_handler(state=Form.admin_broadcast)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    # Разделяем текст и URL если есть
    parts = message.text.split('|')
    text = parts[0].strip()
    url = parts[1].strip() if len(parts) > 1 else None

    # Получаем всех пользователей
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    success = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(
                chat_id=user[0],
                text=text,
                reply_markup=broadcast_keyboard(url),
                parse_mode="HTML"
            )
            success += 1
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
            failed += 1
        await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты Telegram

    await state.finish()
    await message.answer(
        f"📢 Рассылка завершена!\n\nУспешно: {success}\nНе удалось: {failed}",
        reply_markup=admin_keyboard()
    )


# Обработчик кнопки "Прочитано"
@dp.callback_query_handler(lambda c: c.data == 'broadcast_read')
async def broadcast_read(callback_query: types.CallbackQuery):
    try:
        await bot.delete_message(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
        )
    except Exception as e:
        logger.error(f"Ошибка удаления сообщения: {e}")
    await callback_query.answer()

# =====================
# ЗАПУСК БОТА
# =====================

if __name__ == '__main__':
    logger.info("Starting Nemezida RML Bot...")
    executor.start_polling(dp, skip_updates=True)