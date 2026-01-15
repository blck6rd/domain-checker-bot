#!/usr/bin/env python3
"""
Telegram бот для проверки срока действия доменов.
С поддержкой аккаунтов и поиском доменов.
"""

import json
import logging
import os
from datetime import time, datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

from config import BOT_TOKEN, EXPIRY_WARNING_DAYS
from domain_manager import DomainManager
from whois_checker import check_domain, format_domain_info

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Файл для хранения chat_id пользователей
USERS_FILE = "users.json"

# Инициализация менеджера доменов
domain_manager = DomainManager()

# Состояния для ConversationHandler
WAITING_DOMAIN_ADD = 1
WAITING_DOMAIN_CHECK = 2
WAITING_DOMAIN_EDIT_NEW = 3
WAITING_DOMAIN_FIND = 4

# Текст кнопок
BTN_CHECK_ALL = "🔍 Проверить все"
BTN_EXPIRING = "⚠️ Истекающие"
BTN_LIST = "📋 Список"
BTN_CHECK_ONE = "🔎 Проверить один"
BTN_ADD = "➕ Добавить"
BTN_REMOVE = "➖ Удалить"
BTN_FIND = "🔎 Найти домен"
BTN_ACCOUNTS = "👤 Аккаунты"
BTN_HELP = "❓ Помощь"
BTN_CANCEL = "❌ Отмена"


# === Управление пользователями ===

def load_users() -> set:
    """Загружает список chat_id пользователей."""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get("users", []))
        except:
            pass
    return set()


def save_users(users: set):
    """Сохраняет список пользователей."""
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": list(users)}, f)


def add_user(chat_id: int):
    """Добавляет пользователя в список для уведомлений."""
    users = load_users()
    users.add(chat_id)
    save_users(users)


# === Клавиатуры ===

def get_main_keyboard():
    """Постоянная клавиатура внизу экрана."""
    keyboard = [
        [BTN_CHECK_ALL, BTN_EXPIRING],
        [BTN_FIND, BTN_CHECK_ONE],
        [BTN_LIST, BTN_ACCOUNTS],
        [BTN_ADD, BTN_REMOVE],
        [BTN_HELP],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены."""
    keyboard = [[BTN_CANCEL]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# === Автопроверка ===

async def daily_check(context: ContextTypes.DEFAULT_TYPE):
    """Ежедневная проверка доменов."""
    logger.info("Запуск ежедневной проверки доменов...")

    domains = domain_manager.get_all_domains()
    if not domains:
        logger.info("Список доменов пуст, пропускаем проверку")
        return

    # Проверяем домены
    expiring_results = []
    for domain in domains:
        info = check_domain(domain, EXPIRY_WARNING_DAYS)
        if info.is_expiring_soon:
            account = domain_manager.find_domain(domain)
            result = format_domain_info(info)
            if account:
                result += f"\n   📧 {account}"
            expiring_results.append(result)

    if not expiring_results:
        logger.info("Нет истекающих доменов")
        return

    # Формируем сообщение
    message = f"🔔 Ежедневная проверка доменов\n\n"
    message += f"⚠️ Истекают в ближайшие {EXPIRY_WARNING_DAYS} дней:\n\n"
    message += "\n\n".join(expiring_results)

    # Отправляем всем пользователям
    users = load_users()
    for chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            logger.info(f"Уведомление отправлено пользователю {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {chat_id}: {e}")


# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    add_user(update.effective_chat.id)

    stats = domain_manager.get_stats()
    welcome_text = f"""Привет! Я бот для проверки доменов.

📊 Статистика:
   Аккаунтов: {stats['accounts_count']}
   Доменов: {stats['domains_count']}

🔔 Ты подписан на ежедневные уведомления (09:00).

Выбери действие:"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений."""
    add_user(update.effective_chat.id)
    text = update.message.text

    if text == BTN_CHECK_ALL:
        await check_all_domains(update, context)

    elif text == BTN_EXPIRING:
        await show_expiring(update, context)

    elif text == BTN_LIST:
        await list_domains(update, context)

    elif text == BTN_CHECK_ONE:
        await update.message.reply_text(
            "Введи домен для проверки WHOIS:",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_DOMAIN_CHECK

    elif text == BTN_FIND:
        await update.message.reply_text(
            "Введи домен для поиска аккаунта:",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_DOMAIN_FIND

    elif text == BTN_ADD:
        await update.message.reply_text(
            "Введи домен для добавления:",
            reply_markup=get_cancel_keyboard()
        )
        return WAITING_DOMAIN_ADD

    elif text == BTN_REMOVE:
        await show_remove_menu(update, context)

    elif text == BTN_ACCOUNTS:
        await show_accounts(update, context)

    elif text == BTN_HELP:
        await show_help(update, context)

    elif text == BTN_CANCEL:
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    return ConversationHandler.END


async def check_all_domains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет все домены."""
    domains = domain_manager.get_all_domains()

    if not domains:
        await update.message.reply_text(
            "Список доменов пуст.",
            reply_markup=get_main_keyboard()
        )
        return

    await update.message.reply_text(f"⏳ Проверяю {len(domains)} доменов...")

    results = []
    expiring_count = 0

    for domain in domains:
        info = check_domain(domain, EXPIRY_WARNING_DAYS)
        result = format_domain_info(info)
        account = domain_manager.find_domain(domain)
        if account:
            result += f"\n   📧 {account}"
        results.append(result)
        if info.is_expiring_soon:
            expiring_count += 1

    message = "\n\n".join(results)

    if expiring_count > 0:
        message += f"\n\n⚠️ ВНИМАНИЕ: {expiring_count} доменов истекают!"

    # Разбиваем если слишком длинное
    if len(message) > 4000:
        chunks = []
        current = ""
        for r in results:
            if len(current) + len(r) > 3900:
                chunks.append(current)
                current = r
            else:
                current += "\n\n" + r if current else r
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                await update.message.reply_text(chunk, reply_markup=get_main_keyboard())
            else:
                await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(message, reply_markup=get_main_keyboard())


async def show_expiring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает истекающие домены."""
    domains = domain_manager.get_all_domains()

    if not domains:
        await update.message.reply_text("Список доменов пуст.", reply_markup=get_main_keyboard())
        return

    await update.message.reply_text("⏳ Ищу истекающие домены...")

    expiring_results = []
    for domain in domains:
        info = check_domain(domain, EXPIRY_WARNING_DAYS)
        if info.is_expiring_soon:
            result = format_domain_info(info)
            account = domain_manager.find_domain(domain)
            if account:
                result += f"\n   📧 {account}"
            expiring_results.append(result)

    if not expiring_results:
        await update.message.reply_text(
            f"✅ Нет доменов, истекающих в ближайшие {EXPIRY_WARNING_DAYS} дней.",
            reply_markup=get_main_keyboard()
        )
    else:
        message = f"⚠️ Истекают в ближайшие {EXPIRY_WARNING_DAYS} дней:\n\n"
        message += "\n\n".join(expiring_results)
        await update.message.reply_text(message, reply_markup=get_main_keyboard())


async def list_domains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доменов по аккаунтам."""
    accounts = domain_manager.get_all_accounts()

    if not accounts:
        await update.message.reply_text(
            "Список доменов пуст.",
            reply_markup=get_main_keyboard()
        )
        return

    stats = domain_manager.get_stats()
    message = f"📋 Все домены ({stats['domains_count']}):\n\n"

    for account, domains in accounts.items():
        message += f"📧 {account} ({len(domains)}):\n"
        for domain in domains[:5]:  # Показываем первые 5
            message += f"   • {domain}\n"
        if len(domains) > 5:
            message += f"   ... и ещё {len(domains) - 5}\n"
        message += "\n"

    if len(message) > 4000:
        message = f"📋 Статистика ({stats['domains_count']} доменов):\n\n"
        for account, count in stats['accounts'].items():
            message += f"📧 {account}: {count} доменов\n"

    await update.message.reply_text(message, reply_markup=get_main_keyboard())


async def show_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список аккаунтов с кнопками."""
    accounts = domain_manager.get_all_accounts()

    if not accounts:
        await update.message.reply_text("Нет аккаунтов.", reply_markup=get_main_keyboard())
        return

    keyboard = []
    for account, domains in accounts.items():
        keyboard.append([InlineKeyboardButton(
            f"📧 {account} ({len(domains)})",
            callback_data=f"acc_{account[:50]}"
        )])

    await update.message.reply_text(
        "👤 Выбери аккаунт для просмотра доменов:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_remove_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает аккаунты для выбора домена на удаление."""
    accounts = domain_manager.get_all_accounts()

    if not accounts:
        await update.message.reply_text("Список доменов пуст.", reply_markup=get_main_keyboard())
        return

    keyboard = []
    for account in accounts.keys():
        keyboard.append([InlineKeyboardButton(
            f"📧 {account}",
            callback_data=f"remacc_{account[:40]}"
        )])

    await update.message.reply_text(
        "Выбери аккаунт:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку."""
    help_text = """❓ Справка

🔍 Проверить все - WHOIS всех доменов
⚠️ Истекающие - домены < 31 день
🔎 Найти домен - поиск аккаунта по домену
🔎 Проверить один - WHOIS любого домена
📋 Список - все домены по аккаунтам
👤 Аккаунты - выбор аккаунта
➕ Добавить - добавить домен
➖ Удалить - удалить домен

🔔 Автопроверка: каждый день в 09:00

Индикаторы:
🟢 более 60 дней
🟡 31-60 дней
🔴 менее 31 дня"""
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())


async def handle_domain_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск домена и его аккаунта."""
    text = update.message.text

    if text == BTN_CANCEL:
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    domain = text.strip().lower()

    # Точный поиск
    account = domain_manager.find_domain(domain)

    if account:
        message = f"✅ Домен найден!\n\n"
        message += f"🌐 {domain}\n"
        message += f"📧 Аккаунт: {account}"
    else:
        # Поиск по частичному совпадению
        results = domain_manager.search_domains(domain)
        if results:
            message = f"🔍 Похожие домены ({len(results)}):\n\n"
            for d, acc in results[:10]:
                message += f"🌐 {d}\n   📧 {acc}\n\n"
            if len(results) > 10:
                message += f"... и ещё {len(results) - 10}"
        else:
            message = f"❌ Домен {domain} не найден в базе."

    await update.message.reply_text(message, reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def handle_domain_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление домена."""
    text = update.message.text

    if text == BTN_CANCEL:
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    domain = text.strip().lower()
    success, message = domain_manager.add_domain(domain)

    emoji = "✅" if success else "❌"
    await update.message.reply_text(f"{emoji} {message}", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def handle_domain_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка одного домена."""
    text = update.message.text

    if text == BTN_CANCEL:
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    domain = text.strip().lower()
    await update.message.reply_text(f"⏳ Проверяю {domain}...")

    info = check_domain(domain, EXPIRY_WARNING_DAYS)
    result = format_domain_info(info)

    # Проверяем, есть ли в нашей базе
    account = domain_manager.find_domain(domain)
    if account:
        result += f"\n   📧 {account}"

    if info.is_expiring_soon:
        result += f"\n\n⚠️ Истекает менее чем через {EXPIRY_WARNING_DAYS} дней!"

    await update.message.reply_text(result, reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def handle_domain_edit_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод нового имени домена."""
    text = update.message.text

    if text == BTN_CANCEL:
        await update.message.reply_text("Отменено.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    new_domain = text.strip().lower()
    old_domain = context.user_data.get("edit_old_domain", "")

    success, message = domain_manager.update_domain(old_domain, new_domain)

    emoji = "✅" if success else "❌"
    await update.message.reply_text(f"{emoji} {message}", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def inline_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик inline-кнопок."""
    query = update.callback_query
    await query.answer()

    action = query.data

    # Просмотр доменов аккаунта
    if action.startswith("acc_"):
        account_prefix = action[4:]
        accounts = domain_manager.get_all_accounts()

        # Находим полный email по префиксу
        account = None
        for acc in accounts.keys():
            if acc.startswith(account_prefix) or acc[:50] == account_prefix:
                account = acc
                break

        if account and account in accounts:
            domains = accounts[account]
            message = f"📧 {account}\n\n"
            message += f"Доменов: {len(domains)}\n\n"
            for d in domains:
                message += f"• {d}\n"

            if len(message) > 4000:
                message = f"📧 {account}\n\nДоменов: {len(domains)}\n\n"
                for d in domains[:50]:
                    message += f"• {d}\n"
                message += f"\n... и ещё {len(domains) - 50}"

            await query.edit_message_text(message)
        else:
            await query.edit_message_text("Аккаунт не найден.")

    # Выбор аккаунта для удаления
    elif action.startswith("remacc_"):
        account_prefix = action[7:]
        accounts = domain_manager.get_all_accounts()

        account = None
        for acc in accounts.keys():
            if acc.startswith(account_prefix) or acc[:40] == account_prefix:
                account = acc
                break

        if account and account in accounts:
            domains = accounts[account]
            keyboard = []
            for domain in domains[:20]:  # Макс 20 кнопок
                keyboard.append([InlineKeyboardButton(
                    f"❌ {domain}",
                    callback_data=f"del_{domain[:50]}"
                )])

            if len(domains) > 20:
                await query.edit_message_text(
                    f"Слишком много доменов ({len(domains)}). Показаны первые 20:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await query.edit_message_text(
                    f"📧 {account}\nВыбери домен для удаления:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await query.edit_message_text("Аккаунт не найден.")

    # Удаление домена
    elif action.startswith("del_"):
        domain_prefix = action[4:]
        # Ищем домен по префиксу
        all_domains = domain_manager.get_all_domains()
        domain = None
        for d in all_domains:
            if d.startswith(domain_prefix) or d[:50] == domain_prefix:
                domain = d
                break

        if domain:
            success, message = domain_manager.remove_domain(domain)
            emoji = "✅" if success else "❌"
            await query.edit_message_text(f"{emoji} {message}")
        else:
            await query.edit_message_text("Домен не найден.")

    elif action.startswith("edit_"):
        domain = action[5:]
        context.user_data["edit_old_domain"] = domain
        await query.edit_message_text(f"Редактирование: {domain}\n\nВведи новое имя:")
        return WAITING_DOMAIN_EDIT_NEW

    return ConversationHandler.END


def main():
    """Запуск бота."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ОШИБКА: Не установлен токен бота!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем ежедневную проверку в 09:00
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_check,
        time=time(hour=9, minute=0, second=0),
        name="daily_domain_check"
    )
    logger.info("Ежедневная проверка запланирована на 09:00")

    # ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
            CallbackQueryHandler(inline_button_handler),
        ],
        states={
            WAITING_DOMAIN_ADD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_domain_add),
            ],
            WAITING_DOMAIN_CHECK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_domain_check),
            ],
            WAITING_DOMAIN_EDIT_NEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_domain_edit_new),
            ],
            WAITING_DOMAIN_FIND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_domain_find),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(f"^{BTN_CANCEL}$"), handle_message),
        ],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    print("Бот запущен...")
    print(f"Доменов: {domain_manager.get_domains_count()}")
    print(f"Аккаунтов: {domain_manager.get_accounts_count()}")
    print("Ежедневная проверка: 09:00")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
