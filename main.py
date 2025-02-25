import logging
import json
import os
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Замените на ваш токен
TOKEN = 'TOKEN'
SUBSCRIBERS_FILE = 'subscribers.json'
INDEX_FILE = 'index.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(subscribers, f)

def load_index():
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, 'r') as f:
            return json.load(f).get('index', 0)
    return 0

def save_index(index):
    with open(INDEX_FILE, 'w') as f:
        json.dump({'index': index}, f)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("У вас нет username, невозможно подписаться.")
        return

    subscribers = load_subscribers()
    if username in subscribers:
        await update.message.reply_text("Вы уже подписаны.")
    else:
        subscribers.append(username)
        save_subscribers(subscribers)
        await update.message.reply_text("Вы успешно подписались.")

async def weekly_task(context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    if not subscribers:
        logger.info("Нет подписчиков для выбора.")
        return
    index = load_index()
    selected_user = subscribers[index % len(subscribers)]
    index = (index + 1) % len(subscribers)
    save_index(index)

    message_text = f"На этой неделе ответственный за вынос мусора: @{selected_user}"
    chat_id = context.job.context  # chat_id передаётся через context
    message = await context.bot.send_message(chat_id=chat_id, text=message_text)

    try:
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as e:
        logger.error("Ошибка при закреплении сообщения: %s", e)

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Всем привет! Я буду каждую неделю тегать того, кто должен вынести мусор. Подпишитесь, пожалуйста, с помощью команды /subscribe.")

async def subscribers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    if not subscribers:
        await update.message.reply_text("Пока никто не подписался.")
    else:
        message = "Список подписчиков:\n" + "\n".join(f"@ {username}" for username in subscribers)
        await update.message.reply_text(message)

async def next_cleaner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await assign_next_cleaner(chat_id, context)

async def assign_next_cleaner(chat_id, context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    if not subscribers:
        await context.bot.send_message(chat_id=chat_id, text="Нет подписчиков для выбора.")
        return

    index = load_index()
    selected_user = subscribers[index % len(subscribers)]
    index = (index + 1) % len(subscribers)
    save_index(index)

    message_text = f"На этой неделе ответственный за вынос мусора: @{selected_user}"
    message = await context.bot.send_message(chat_id=chat_id, text=message_text)
    try:
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=message.message_id)
    except Exception as e:
        logger.error("Ошибка при закреплении сообщения: %s", e)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    if not username:
        await update.message.reply_text("У вас нет username, невозможно отписаться.")
        return

    subscribers = load_subscribers()
    if username not in subscribers:
        await update.message.reply_text("Вы не подписаны.")
    else:
        subscribers.remove(username)
        save_subscribers(subscribers)
        await update.message.reply_text("Вы успешно отписались.")


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_bot))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("subscribers", subscribers_list))
    application.add_handler(CommandHandler("next_cleaner", next_cleaner))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Укажите идентификатор чата, где бот должен публиковать сообщения.
    # Для групповых чатов chat_id обычно отрицательный.
    chat_id = -123456789  # Замените на реальный chat_id вашей группы

    # Планирование еженедельной задачи: каждый понедельник в 09:00
    target_time = datetime.time(hour=9, minute=0, second=0)
    application.job_queue.run_daily(weekly_task, time=target_time, days=(0,), data=chat_id)

    application.run_polling()

if __name__ == '__main__':
    main()
