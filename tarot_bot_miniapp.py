import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN   = "ВАШ_ТОКЕН"
ADMIN_ID    = 123456789
MINIAPP_URL = "https://ВАШ_USERNAME.github.io/tarot-miniapp/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

requests_db = {}
request_counter = 0

STATUSES = {
    "pending":  "🟡 Ожидает",
    "accepted": "🟢 Принято",
    "done":     "✅ Выполнено",
}

def next_id():
    global request_counter
    request_counter += 1
    return request_counter

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 Записаться на расклад", web_app=WebAppInfo(url=MINIAPP_URL))],
        [InlineKeyboardButton("📋 Мои заявки", callback_data="my_requests")],
        [InlineKeyboardButton("❓ Что такое таро?", callback_data="about")],
    ])
    await update.message.reply_text(
        f"Привет, {user.first_name} 🌙\n\n"
        "Я помогу тебе записаться на расклад таро.\n"
        "Нажми кнопку ниже — откроется форма прямо здесь, в Telegram.",
        reply_markup=keyboard
    )

async def handle_web_app_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    raw  = update.effective_message.web_app_data.data
    user = update.effective_user
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    req_id = next_id()
    requests_db[req_id] = {
        "id":       req_id,
        "user_id":  user.id,
        "spread":   data.get("spread",   "—"),
        "price":    data.get("price",    "—"),
        "name":     data.get("name",     "—"),
        "contact":  data.get("contact",  "—"),
        "question": data.get("question", "—"),
        "tg_user":  data.get("tg_user",  f"@{user.username or '—'} ({user.id})"),
        "status":   "pending",
    }
    r = requests_db[req_id]

    await update.message.reply_text(
        f"✨ Заявка №{req_id} принята!\n\n"
        f"🃏 {r['spread']} — {r['price']}\n\n"
        "Я свяжусь с тобой совсем скоро 🌙"
    )

    admin_text = (
        f"🔮 *Новая заявка №{req_id}*\n\n"
        f"🃏 *Расклад:* {r['spread']}\n"
        f"💰 *Цена:* {r['price']}\n"
        f"👤 *Имя:* {r['name']}\n"
        f"📱 *Контакт:* {r['contact']}\n"
        f"💬 *Вопрос:* {r['question']}\n"
        f"🔗 *Telegram:* {r['tg_user']}\n\n"
        f"Статус: {STATUSES['pending']}"
    )
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Принять",   callback_data=f"setstatus:{req_id}:accepted"),
            InlineKeyboardButton("✅ Выполнено", callback_data=f"setstatus:{req_id}:done"),
        ]
    ])
    try:
        await ctx.bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=admin_kb)
    except Exception as e:
        log.error(f"Не удалось уведомить админа: {e}")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("setstatus:"):
        _, req_id_str, new_status = data.split(":")
        req_id = int(req_id_str)
        if req_id not in requests_db:
            await q.edit_message_text("❌ Заявка не найдена.")
            return
        r = requests_db[req_id]
        r["status"] = new_status
        updated_text = (
            f"🔮 *Заявка №{req_id}*\n\n"
            f"🃏 *Расклад:* {r['spread']}\n"
            f"💰 *Цена:* {r['price']}\n"
            f"👤 *Имя:* {r['name']}\n"
            f"📱 *Контакт:* {r['contact']}\n"
            f"💬 *Вопрос:* {r['question']}\n"
            f"🔗 *Telegram:* {r['tg_user']}\n\n"
            f"Статус: {STATUSES[new_status]}"
        )
        if new_status == "accepted":
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Выполнено", callback_data=f"setstatus:{req_id}:done")]])
        else:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("☑️ Закрыто", callback_data="noop")]])
        await q.edit_message_text(updated_text, parse_mode="Markdown", reply_markup=kb)
        notify = {
            "accepted": f"🟢 Твоя заявка №{req_id} принята!\n\nСкоро выйду на связь 🌙",
            "done":     f"✅ Расклад №{req_id} выполнен!\n\nСпасибо, что обратилась 🔮",
        }
        try:
            await ctx.bot.send_message(r["user_id"], notify[new_status])
        except Exception as e:
            log.error(f"Не удалось уведомить пользователя: {e}")
        return

    if data == "my_requests":
        user_id = q.from_user.id
        user_requests = [r for r in requests_db.values() if r["user_id"] == user_id]
        if not user_requests:
            await q.edit_message_text(
                "У тебя пока нет заявок.\n\nЗапишись на расклад 🔮",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔮 Записаться", web_app=WebAppInfo(url=MINIAPP_URL))]])
            )
            return
        lines = ["*Твои заявки:*\n"]
        for r in reversed(user_requests):
            lines.append(f"№{r['id']} · {r['spread']} · {r['price']}\n└ {STATUSES[r['status']]}\n")
        await q.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="back_start")]])
        )
        return

    if data == "about":
        await q.edit_message_text(
            "🃏 *Таро* — система из 78 карт, которая помогает\n"
            "взглянуть на ситуацию с другой стороны.\n\n"
            "Расклад — это не предсказание судьбы,\n"
            "а живой разговор о том, что происходит у тебя внутри.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔮 Записаться", web_app=WebAppInfo(url=MINIAPP_URL))],
                [InlineKeyboardButton("← Назад", callback_data="back_start")],
            ])
        )
        return

    if data == "back_start":
        await q.edit_message_text(
            "Выбери действие 🌙",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔮 Записаться на расклад", web_app=WebAppInfo(url=MINIAPP_URL))],
                [InlineKeyboardButton("📋 Мои заявки", callback_data="my_requests")],
                [InlineKeyboardButton("❓ Что такое таро?", callback_data="about")],
            ])
        )
        return

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.add_handler(CallbackQueryHandler(handle_callback))
    log.info("Бот запущен 🔮")
    app.run_polling()

if __name__ == "__main__":
    main()
