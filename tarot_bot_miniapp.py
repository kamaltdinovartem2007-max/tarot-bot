import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, PicklePersistence

BOT_TOKEN   = "8663679950:AAH_Tnx9mtotMohwyc_KP2OK4YTuQTIq7Qk"
ADMIN_ID    = 1470728379
MINIAPP_URL = "https://kamaltdinovartem2007-max.github.io/tarot-miniapp/"

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

async def handle_web_app_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message.web_app_data:
        return
    raw = update.effective_message.web_app_data.data
    user = update.effective_user
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    if "requests" not in ctx.bot_data:
        ctx.bot_data["requests"] = {}
    uid = str(user.id)
    if uid not in ctx.bot_data["requests"]:
        ctx.bot_data["requests"][uid] = []
    ctx.bot_data["requests"][uid].append({
        "id":     len(ctx.bot_data["requests"][uid]) + 1,
        "spread": data.get("spread", "—"),
        "price":  data.get("price",  "—"),
        "status": "pending",
    })

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("accept:") or data.startswith("done:"):
        parts = data.split(":")
        action = parts[0]
        client_id = int(parts[1]) if parts[1] else None
        new_status = "accepted" if action == "accept" else "done"
        status_label = STATUSES[new_status]

        # Парсим заявку из текста сообщения и сохраняем в историю
        if client_id:
            uid = str(client_id)
            if "requests" not in ctx.bot_data:
                ctx.bot_data["requests"] = {}

            msg_text = q.message.text
            spread = "—"
            price  = "—"
            for line in msg_text.split("\n"):
                if "Расклад:" in line: spread = line.split("Расклад:")[-1].strip()
                if "Цена:"    in line: price  = line.split("Цена:")[-1].strip()

            if uid not in ctx.bot_data["requests"]:
                ctx.bot_data["requests"][uid] = []

            # Проверяем есть ли уже такая заявка
            existing = ctx.bot_data["requests"][uid]
            found = False
            for r in existing:
                if r["spread"] == spread and r["status"] == "pending":
                    r["status"] = new_status
                    found = True
                    break
            if not found:
                existing.append({
                    "id":     len(existing) + 1,
                    "spread": spread,
                    "price":  price,
                    "status": new_status,
                })

        # Обновляем сообщение у девушки
        old_text = q.message.text
        new_text = old_text.replace("🟡 Ожидает", status_label).replace("🟢 Принято", status_label)

        if new_status == "accepted":
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Выполнено", callback_data=f"done:{client_id}")
            ]])
        else:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("☑️ Закрыто", callback_data="noop")
            ]])

        try:
            await q.edit_message_text(new_text, reply_markup=kb)
        except Exception:
            pass

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

    if data == "my_requests":
        user_id = q.from_user.id
        uid = str(user_id)
        requests = ctx.bot_data.get("requests", {}).get(uid, [])

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
        for r in reversed(requests):
            lines.append(f"№{r['id']} · {r['spread']} · {r['price']}\n└ {STATUSES[r['status']]}\n")

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
    persistence = PicklePersistence(filepath="bot_data.pkl")
    app = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_web_app_data))
    app.add_handler(CallbackQueryHandler(handle_callback))
    log.info("Бот запущен 🔮")
    app.run_polling()

if __name__ == "__main__":
    main()
