"""
🔮 Tarot Bot — с кнопкой Mini App
Установка: pip install python-telegram-bot==20.7
Запуск:    python tarot_bot.py

Что заполнить:
  BOT_TOKEN    — токен от @BotFather
  ADMIN_ID     — твой Telegram ID (узнай у @userinfobot)
  MINIAPP_URL  — URL твоего GitHub Pages, например:
                 https://username.github.io/tarot-miniapp/
"""

import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ─── Настройки ────────────────────────────────────────────────────────────────
BOT_TOKEN   = "8663679950:AAH_Tnx9mtotMohwyc_KP2OK4YTuQTIq7Qk"
ADMIN_ID    = 1470728379
MINIAPP_URL = "https://kamaltdinovartem2007-max.github.io/tarot-miniapp/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🔮 Записаться на расклад",
            web_app=WebAppInfo(url=MINIAPP_URL)
        )],
        [InlineKeyboardButton("❓ Что такое таро?", callback_data="about")]
    ])

    await update.message.reply_text(
        f"Привет, {user.first_name} 🌙\n\n"
        "Я помогу тебе записаться на расклад таро.\n"
        "Нажми кнопку ниже — откроется форма прямо здесь, в Telegram.",
        reply_markup=keyboard
    )


# ─── Получение данных из Mini App ─────────────────────────────────────────────
async def handle_web_app_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Когда пользователь нажимает «Отправить» в Mini App,
    вызывается tg.sendData() — и бот получает это сообщение.
    """
    raw  = update.effective_message.web_app_data.data
    user = update.effective_user

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error(f"Не удалось разобрать данные: {raw}")
        return

    spread   = data.get("spread",   "—")
    name     = data.get("name",     "—")
    contact  = data.get("contact",  "—")
    question = data.get("question", "—")
    tg_user  = data.get("tg_user",  "—")

    # Подтверждение пользователю
    await update.message.reply_text(
        "✨ Заявка принята!\n\n"
        "Я свяжусь с тобой совсем скоро, чтобы согласовать время.\n\n"
        "До встречи в картах 🌙🔮"
    )

    # Уведомление администратору
    admin_text = (
        "🔮 *Новая заявка на расклад!*\n\n"
        f"🃏 *Расклад:* {spread}\n"
        f"👤 *Имя:* {name}\n"
        f"📱 *Контакт:* {contact}\n"
        f"💬 *Вопрос:* {question}\n"
        f"🔗 *Telegram:* {tg_user}"
    )
    try:
        await ctx.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"Не удалось уведомить администратора: {e}")


# ─── /about (callback) ────────────────────────────────────────────────────────
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()

    if q.data == "about":
        await q.edit_message_text(
            "🃏 *Таро* — система из 78 карт, которая помогает\n"
            "взглянуть на ситуацию с другой стороны.\n\n"
            "Расклад — это не предсказание судьбы,\n"
            "а живой разговор о том, что происходит у тебя внутри.\n\n"
            "Нажми кнопку ниже, чтобы записаться 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔮 Записаться на расклад",
                    web_app=WebAppInfo(url=MINIAPP_URL)
                )]
            ])
        )


# ─── Запуск ───────────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info("Бот с Mini App запущен 🔮")
    app.run_polling()


if __name__ == "__main__":
    main()
