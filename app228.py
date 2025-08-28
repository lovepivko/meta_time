import os
import requests
import telebot
from flask import Flask, request

# --- Настройки из .env ---
TOKEN = os.getenv("BOT_TOKEN")
MTFL_MERCHANT_ID = os.getenv("MTFL_MERCHANT_ID")
MTFL_TOKEN = os.getenv("MTFL_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен!")
if not MTFL_MERCHANT_ID or not MTFL_TOKEN:
    raise ValueError("❌ MTFL_MERCHANT_ID или MTFL_TOKEN не установлены!")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Установка webhook ---
WEBHOOK_URL = f"https://example-meta.onrender.com/{TOKEN}"
set_hook = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL}
)
print(f"📡 Webhook установлен: {WEBHOOK_URL}")
print(f"✅ Ответ Telegram: {set_hook.text}")


@app.route("/", methods=["GET", "HEAD"])
def index():
    return "🤖 MTFL Bot работает!"


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get("content-type", "").startswith("application/json"):
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
        return '', 200
    return 'Unsupported Media Type', 415


# --- /start ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "💸 Введите сумму пополнения в рублях (например: 1000):")


# --- Обработка суммы ---
@bot.message_handler(func=lambda m: True)
def handle_amount(message):
    try:
        amount = int(float(message.text.strip().replace(",", ".")))
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть больше нуля.")
            return

        payload = {
            "merchantId": int(MTFL_MERCHANT_ID),
            "token": MTFL_TOKEN,
            "externalId": f"tg_{message.from_user.id}_{message.message_id}",
            "amount": amount,
            "type": "sbp",
            "client": {
                "name": f"tg_user_{message.from_user.id}",
                "email": f"user{message.from_user.id}@example.com"
            },
            "trafficType": "web"
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        resp = requests.post("https://api.mtfl.app/v2/payments", json=payload, headers=headers)
        data = resp.json()
        print("📤 Ответ MTFL:", resp.status_code, data)

        if resp.ok and data.get("status") is True:
            trx = data["data"]["transaction"]
            details = trx.get("paymentDetails", {})

            sbp_phone = details.get("sbpPhone", "—")
            credit_card = details.get("creditCard", "—")
            bank_name = details.get("bankName", "—")
            customer_name = details.get("customerName", "—")

            bot.send_message(
                message.chat.id,
                f"✅ Заявка создана (ID: {trx.get('id', '—')})\n"
                f"💰 Сумма: {trx['amount'].get('rub', amount)} RUB\n\n"
                f"📱 Телефон для СБП: `{sbp_phone}`\n"
                f"💳 Карта: `{credit_card}`\n"
                f"🏦 Банк: {bank_name}\n"
                f"👤 Получатель: {customer_name}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "❌ Не удалось создать заявку.")
            print("❌ Ошибка MTFL:", resp.status_code, data)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму, например: 1500")
    except Exception as e:
        print("⚠️ Ошибка обработки:", e)
        bot.send_message(message.chat.id, "❌ Произошла ошибка при создании заявки.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



