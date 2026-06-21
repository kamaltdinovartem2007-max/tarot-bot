import json 
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN   = "8663679950:AAH_Tnx9mtotMohwyc_KP2OK4YTuQTIq7Qk"
ADMIN_ID    = 1470728379
MINIAPP_URL = "https://kamaltdinovartem2007-max.github.io/tarot-miniapp/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# Хранилище заявок: { user_id: [ {spread, price, status}, ... ] }
user_requests = {}

STATUSES = {
    "pending":  "🟡 Ожидает",
    "accepted": "🟢 Принято",
    "done":     "✅ Выполнено",
}

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

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data

    # Кнопки статуса от девушки
    if data.startswith("accept:") or data.startswith("done:"):
        action, client_id_str = data.split(":")
        client_id = int(client_id_str) if client_id_str else None
        new_status = "accepted" if action == "accept" else "done"
        status_label = STATUSES[new_status]

        # Обновляем последнюю заявку клиента
        if client_id and client_id in user_requests and user_requests[client_id]:
            user_requests[client_id][-1]["status"] = new_status

        # Обновляем сообщение у девушки
        old_text = q.message.text
        new_text = old_text.replace("🟡 Ожидает", status_label).replace("🟢 Принято", status_label)

        if new_status == "accepted":
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Выполнено", callback_data=f"done:{client_id_str}")
            ]])
        else:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("☑️ Закрыто", callback_data="noop")
            ]])

        await q.edit_message_text(new_text, reply_markup=kb)

        # Уведомление клиенту
        if client_id:
            notify = {
                "accepted": "🟢 Твоя заявка принята!\n\nСкоро выйду на связь 🌙",
                "done":     "✅ Расклад выполнен!\n\nСпасибо, что обратилась 🔮",
            }
            try:
                await ctx.bot.send_message(client_id, notify[new_status])
            except Exception as e:
                log.error(f"Не удалось уведомить клиента: {e}")
        return

    # Мои заявки
    if data == "my_requests":
        user_id = q.from_user.id
        requests = user_requests.get(user_id, [])

        if not requests:
            await q.edit_message_text(
                "У тебя пока нет заявок.\n\nЗапишись на расклад 🔮",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔮 Записаться", web_app=WebAppInfo(url=MINIAPP_URL))
                ]])
            )
            return

        lines = ["*Твои заявки:*\n"]
        for i, r in enumerate(reversed(requests), 1):
            lines.append(f"№{i} · {r['spread']} · {r['price']}\n└ {STATUSES[r['status']]}\n")

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔮 Записаться", web_app=WebAppInfo(url=MINIAPP_URL))],
                [InlineKeyboardButton("← Главное меню", callback_data="back_start")],
            ])
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

    if data == "noop":
        return

# Получение данных из Mini App (для сохранения истории)
async def handle_web_app_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message.web_app_data:
        return
    raw = update.effective_message.web_app_data.data
    user = update.effective_user
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    # Сохраняем заявку в историю
    if user.id not in user_requests:
        user_requests[user.id] = []
    user_requests[user.id].append({
        "spread": data.get("spread", "—"),
        "price":  data.get("price",  "—"),
        "status": "pending",
    })

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_web_app_data))
    app.add_handler(CallbackQueryHandler(handle_callback))
    log.info("Бот запущен 🔮")
    app.run_polling()

if __name__ == "__main__":
    main()
