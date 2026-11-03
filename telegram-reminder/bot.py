import logging
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import llm
import storage


def local_format(epoch: int) -> str:
    dt = datetime.fromtimestamp(epoch, timezone.utc).astimezone(ZoneInfo(config.TIMEZONE))
    return dt.strftime("%d.%m.%Y %H:%M")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот-напоминалка.\n\n"
        "Просто напиши, что и когда напомнить, например:\n"
        "• «Напомни позвонить маме завтра в 18:00»\n"
        "• «Напомни 5 числа вечером купить билеты»\n"
        "• «Напомни через час выпить таблетку»\n\n"
        "Команды:\n"
        "/list — мои напоминания\n"
        "/del <номер> — удалить напоминание"
    )


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = storage.list_pending(update.effective_chat.id, int(time.time()))
    if not rows:
        await update.message.reply_text("У тебя нет активных напоминаний.")
        return
    lines = [f"#{r['id']} • {local_format(r['remind_at'])} — {r['text']}" for r in rows]
    await update.message.reply_text(
        "📋 Активные напоминания:\n\n" + "\n".join(lines) + "\n\nУдалить: /del <номер>"
    )


async def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажи номер: /del 12")
        return
    try:
        rid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер должен быть числом: /del 12")
        return
    if storage.delete_reminder(rid, update.effective_chat.id):
        await update.message.reply_text("🗑 Напоминание удалено.")
    else:
        await update.message.reply_text("Не нашёл такое напоминание.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()

    try:
        parsed = llm.parse_message(raw)
    except Exception as e:
        logging.exception("Ошибка парсинга сообщения")
        await update.message.reply_text(f"😕 Не смог разобрать сообщение: {e}")
        return

    if parsed is None:
        await update.message.reply_text(
            "Не понял, что и когда напомнить.\n"
            "Например: «Напомни позвонить маме завтра в 18:00»"
        )
        return

    text, dt_local = parsed
    remind_at = int(dt_local.astimezone(timezone.utc).timestamp())
    now = int(time.time())

    if remind_at <= now:
        await update.message.reply_text("Это время уже в прошлом — напомнить задним числом не получится.")
        return

    storage.add_reminder(update.effective_chat.id, text, remind_at)
    await update.message.reply_text(
        f"✅ Записал: «{text}»\n⏰ {dt_local.strftime('%d.%m.%Y %H:%M')}"
    )


async def tick(context: ContextTypes.DEFAULT_TYPE):
    now = int(time.time())
    for r in storage.due_reminders(now):
        storage.mark_done(r["id"])
        try:
            await context.bot.send_message(r["chat_id"], f"⏰ Напоминание:\n\n{r['text']}")
        except Exception as e:
            storage.mark_pending(r["id"])
            logging.error("Не удалось отправить напоминание #%s: %s", r["id"], e)


def main():
    # Windows-консоль по умолчанию в cp1251 — переводим вывод в UTF-8,
    # чтобы print с эмодзи не падал (сообщения в Telegram и так идут по HTTP в UTF-8).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if not config.BOT_TOKEN:
        print("❌ Ошибка: не задан BOT_TOKEN. Скопируй .env.example в .env и заполни его.")
        return

    storage.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("del", delete_reminder))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(tick, interval=20, first=5)

    print("🤖 Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()