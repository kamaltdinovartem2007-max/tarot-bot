import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN   = "8663679950:AAH_Tnx9mtotMohwyc_KP2OK4YTuQTIq7Qk"
ADMIN_ID    = 1470728379
MINIAPP_URL = "https://kamaltdinovartem2007-max.github.io/tarot-miniapp/"
DB_CHANNEL  = -1004311268357

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

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

async def save_request(ctx, user_id, spread, price, status="pending"):
    """Сохраняем заявку в канал как сообщение"""
    data = json.dumps({
        "user_id": user_id,
        "spread":  spread,
        "price":   price,
        "status":  status,
    }, ensure_ascii=False)
    msg = await ctx.bot.send_message(DB_CHANNEL, f"REQUEST:{data}")
    return msg.message_id

async def get_user_requests(ctx, user_id):
    """Читаем все заявки пользователя из канала"""
    requests = []
    try:
        # Получаем последние 100 сообщений из канала
        async for msg in ctx.bot.get_chat_history(DB_CHANNEL, limit=100):
            if msg.text and msg.text.startswith("REQUEST:"):
                try:
                    data = json.loads(msg.text[8:])
                    if data["user_id"] == user_id:
                        data["msg_id"] = msg.message_id
                        requests.append(data)
                except:
                    pass
    except Exception as e:
        log.error(f"Ошибка чтения истории: {e}")
    return list(reversed(requests))

async def update_request_status(ctx, msg_id, new_status):
    """Обновляем статус заявки"""
    try:
        msg = await ctx.bot.forward_message(DB_CHANNEL, DB_CHANNEL, msg_id)
        # Читаем старое сообщение и обновляем статус
        async for m in ctx.bot.get_chat_history(DB_CHANNEL, limit=200):
            if m.message_id == msg_id and m.text and m.text.startswith("REQUEST:"):
                data = json.loads(m.text[8:])
                data["status"] = new_status
                await ctx.bot.edit_message_text(
                    f"REQUEST:{json.dumps(data, ensure_ascii=False)}",
                    chat_id=DB_CHANNEL,
                    message_id=msg_id
                )
                break
        await ctx.bot.delete_message(DB_CHANNEL, msg.message_id)
    except Exception as e:
        log.error(f"Ошибка обновления статуса: {e}")

async def handle_web_app_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message.web_app_data:
        return
    raw = update.effective_message.web_app_data.data
    user = update.effective_user
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    await save_request(ctx, user.id, data.get("spread", "—"), data.get("price", "—"))

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("accept:") or data.startswith("done:"):
        parts = data.split(":")
        action = parts[0]
        client_id = int(parts[1]) if parts[1] else None
        msg_id = int(parts[2]) if len(parts) > 2 and parts[2] else None
        new_status = "accepted" if action == "accept" else "done"
        status_label = STATUSES[new_status]

        if msg_id:
            await update_request_status(ctx, msg_id, new_status)

        old_text = q.message.text
        new_text = old_text.replace("🟡 Ожидает", status_label).replace("🟢 Принято", status_label)

        if new_status == "accepted":
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Выполнено", callback_data=f"done:{client_id}:{msg_id}")
            ]])
        else:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("☑️ Закрыто", callback_data="noop")
            ]])

        await q.edit_message_text(new_text, reply_markup=kb)

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

    if data == "my_requests":
        user_id = q.from_user.id
        requests = await get_user_requests(ctx, user_id)

        if not requests:
            await q.edit_message_text(
                "У тебя пока нет заявок.\n\nЗапишись на расклад 🔮",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔮 Записаться на расклад", web_app=WebAppInfo(url=MINIAPP_URL))],
                    [InlineKeyboardButton("📋 Мои заявки", callback_data="my_requests")],
                    [InlineKeyboardButton("❓ Что такое таро?", callback_data="about")],
                ])
            )
            return

        lines = ["*Твои заявки:*\n"]
        for i, r in enumerate(requests, 1):
            lines.append(f"№{i} · {r['spread']} · {r['price']}\n└ {STATUSES[r['status']]}\n")

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔮 Записаться на расклад", web_app=WebAppInfo(url=MINIAPP_URL))],
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

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_web_app_data))
    app.add_handler(CallbackQueryHandler(handle_callback))
    log.info("Бот запущен 🔮")
    app.run_polling()

if __name__ == "__main__":
    main()
