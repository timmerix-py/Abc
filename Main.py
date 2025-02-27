import asyncio
import random
import requests
import wikipedia
from telegram import (
    Update, 
    InlineQueryResultArticle, 
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    InlineQueryHandler,
    ContextTypes,
    CallbackQueryHandler
)

# Настройки
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TEMPMAIL_API = "https://www.1secmail.com/api/v1/"
BRAINSHOP_API = "http://api.brainshop.ai/get?bid=178&key=hcKr59qZNM5gTbxX&uid={uid}&msg={msg}"

# Хранилища данных
user_emails = {}
games = {}
current_game_id = 0

wikipedia.set_lang("ru")

# Основные обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используйте инлайн-режим через @вашбот [запрос]")

# Инлайн-режим
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower().strip()
    results = []

    # Tempmail
    if query == "tempmail":
        email = generate_temp_email()
        user_emails[update.inline_query.from_user.id] = email
        results.append(create_email_result(email))
    
    # Checkmail
    elif query == "checkmail":
        email = user_emails.get(update.inline_query.from_user.id)
        if email:
            messages = check_email_messages(email)
            results.append(create_messages_result(messages))
    
    # Википедия
    elif query.startswith("wiki "):
        search_query = query[5:]
        results.extend(get_wikipedia_results(search_query))
    
    # Вопрос к нейросети
    elif query.startswith("ask "):
        question = query[4:]
        answer = get_brain_answer(update.inline_query.from_user.id, question)
        results.append(create_text_result("Ответ", answer))
    
    # Камень-ножницы-бумага
    elif query == "rps":
        global current_game_id
        current_game_id += 1
        games[current_game_id] = {
            "players": {},
            "message_id": None
        }
        results.append(create_game_result(current_game_id))
    
    await update.inline_query.answer(results)

# Игра RPS
async def handle_rps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    game_id = int(query.data.split("_")[1])
    
    if game_id not in games:
        await query.answer("Игра завершена!")
        return
    
    # Обработка выбора
    if query.from_user.id not in games[game_id]["players"]:
        games[game_id]["players"][query.from_user.id] = {
            "name": query.from_user.first_name,
            "choice": None
        }
    
    # Отправка клавиатуры выбора
    keyboard = [
        [
            InlineKeyboardButton("Камень", callback_data=f"choice_{game_id}_rock"),
            InlineKeyboardButton("Ножницы", callback_data=f"choice_{game_id}_scissors"),
            InlineKeyboardButton("Бумага", callback_data=f"choice_{game_id}_paper")
        ]
    ]
    
    await query.edit_message_text(
        text=f"{query.from_user.first_name}, сделайте выбор:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, game_id, choice = query.data.split("_")
    game_id = int(game_id)
    
    games[game_id]["players"][query.from_user.id]["choice"] = choice
    
    # Проверка готовности
    if len(games[game_id]["players"]) < 2:
        await query.answer("Ожидаем второго игрока...")
        return
    
    # Все сделали выбор
    players = list(games[game_id]["players"].values())
    result_text = determine_winner(players[0], players[1])
    
    await query.edit_message_text(
        text=result_text,
        reply_markup=None
    )
    del games[game_id]

# Вспомогательные функции
def generate_temp_email():
    domain = random.choice(["1secmail.com", "1secmail.net", "1secmail.org"])
    username = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=10))
    return f"{username}@{domain}"

def check_email_messages(email):
    username, domain = email.split("@")
    response = requests.get(f"{TEMPMAIL_API}?action=getMessages&login={username}&domain={domain}")
    return response.json() if response.ok else []

def get_wikipedia_results(query):
    try:
        search_results = wikipedia.search(query)
        return [
            InlineQueryResultArticle(
                id=str(idx),
                title=result,
                input_message_content=InputTextMessageContent(
                    wikipedia.summary(result, sentences=3)
            )
            for idx, result in enumerate(search_results[:5])
        ]
    except:
        return []

def get_brain_answer(uid, question):
    response = requests.get(BRAINSHOP_API.format(uid=uid, msg=question))
    return response.json()["cnt"] if response.ok else "Ошибка получения ответа"

def create_email_result(email):
    return InlineQueryResultArticle(
        id="tempmail",
        title="Временная почта",
        input_message_content=InputTextMessageContent(
            f"📧 Ваш временный email:\n`{email}`",
            parse_mode="Markdown"
        )
    )

def create_game_result(game_id):
    return InlineQueryResultArticle(
        id=str(game_id),
        title="🎮 Камень-Ножницы-Бумага",
        input_message_content=InputTextMessageContent("Новая игра началась!"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Присоединиться", 
                callback_data=f"join_{game_id}")
        ]])
    )

def determine_winner(p1, p2):
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    
    if p1["choice"] == p2["choice"]:
        return "🤝 Ничья!"
    
    if beats[p1["choice"]] == p2["choice"]:
        return f"🏆 Победитель: {p1['name']} ({p1['choice']} vs {p2['choice']})"
    else:
        return f"🏆 Победитель: {p2['name']} ({p2['choice']} vs {p1['choice']})"

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_handler))
    application.add_handler(CallbackQueryHandler(handle_rps_callback, pattern="^join_"))
    application.add_handler(CallbackQueryHandler(handle_choice_callback, pattern="^choice_"))
    
    application.run_polling()
