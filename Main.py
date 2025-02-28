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
import os
# Конфигурация
TOKEN = ""
TEMPMAIL_API = "https://www.1secmail.com/api/v1/"
# Инициализация
wikipedia.set_lang("ru")
user_emails = {}
games = {}
game_counter = 0

# Основные обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Используйте инлайн-режим через @вашбот [запрос]")

# Инлайн-обработчик
async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower().strip()
    results = []
    
    try:
        if query == "tempmail":
            results.append(create_temp_email_result(update.inline_query.from_user.id))
            
        elif query == "checkmail":
            results.extend(handle_checkmail(update.inline_query.from_user.id))
            
        elif query.startswith("wiki "):
            results.extend(handle_wiki_query(query[5:]))
            
        elif query.startswith("ask "):
            results.append(handle_ai_query(query[4:], update.inline_query.from_user.id))
            
        elif query == "rps":
            results.append(create_new_game())
            
    except Exception as e:
        print(f"Error: {e}")
        results.append(create_error_result())
    
    await update.inline_query.answer(results)

# Обработчики игр
async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, game_id = query.data.split("_")[:2]
    game_id = int(game_id)
    
    if game_id not in games:
        await query.answer("Игра устарела!")
        return
    
    if action == "join":
        await handle_join_game(query, game_id)
    elif action == "choice":
        await handle_player_choice(query, game_id)

# Вспомогательные функции
def create_temp_email_result(user_id):
    email = generate_email()
    user_emails[user_id] = email
    return InlineQueryResultArticle(
        id="tempmail",
        title="📧 Временная почта",
        input_message_content=InputTextMessageContent(
            f"Ваш временный email:\n`{email}`\nПроверить: @вашбот checkmail",
            parse_mode="Markdown"
        )
    )

def handle_checkmail(user_id):
    if user_id not in user_emails:
        return [create_text_result("❌ Ошибка", "Сначала создайте почту!")]
    
    messages = get_emails(user_emails[user_id])
    if not messages:
        return [create_text_result("📭 Пусто", "Нет новых писем")]
    
    return [
        InlineQueryResultArticle(
            id="mailbox",
            title=f"📫 Писем: {len(messages)}",
            input_message_content=InputTextMessageContent(
                "\n".join([f"От: {m['from']}\nТема: {m['subject']}" for m in messages])
            )
        )
    ]

MEDIAWIKI_API = "https://ru.wikipedia.org/w/api.php"
 # Замените на ваш ключ

# Функция для запросов к Википедии через MediaWiki API
def handle_wiki_query(query):
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": 3  # Ограничиваем количество результатов
    }
    try:
        response = requests.get(MEDIAWIKI_API, params=params)
        data = response.json()
        results = []
        for idx, item in enumerate(data.get("query", {}).get("search", [])):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            results.append(
                InlineQueryResultArticle(
                    id=str(idx),
                    title=title,
                    input_message_content=InputTextMessageContent(snippet),
                    description=snippet[:100]  # Короткое описание для превью
                )
            )
        return results
    except Exception as e:
        print(f"MediaWiki error: {e}")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("deepai")  # Замените на ваш ключ (если требуется)

# Функция для запросов к нейросети через DeepSeek API
from gradio_client import Client

def handle_ai_query(query, user_id):
    try:
        client = Client("featherless-ai/try-this-model")
        # Отправка запроса к нейросети
        result = client.predict(
            message=query,
            model="meta-llama/Llama-3.3-70B-Instruct",
            api_name="/chat"
        )
        return create_text_result("🤖 Ответ", result)
    except Exception as e:
        print(f"AI API error: {e}")
        return create_text_result("❌ Ошибка", "Не удалось получить ответ")

# Вспомогательная функция для создания текстового результата
def create_text_result(title, content):
    return InlineQueryResultArticle(
        id=title[:64],
        title=title,
        input_message_content=InputTextMessageContent(content[:4096])
    )
def create_new_game():
    global game_counter
    game_counter += 1
    games[game_counter] = {"players": {}}
    return InlineQueryResultArticle(
        id=f"game_{game_counter}",
        title="🎮 Новая игра",
        input_message_content=InputTextMessageContent("Камень-Ножницы-Бумага!"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Присоединиться", callback_data=f"join_{game_counter}")
        ]])
    )

async def handle_join_game(query, game_id):
    if len(games[game_id]["players"]) >= 2:
        await query.answer("Игра уже началась!")
        return
    
    user = query.from_user
    games[game_id]["players"][user.id] = {"name": user.first_name, "choice": None}
    
    if len(games[game_id]["players"]) == 1:
        await query.answer("Ожидаем второго игрока...")
        return
    
    await query.edit_message_text(
        text="Выберите вариант:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Камень", callback_data=f"choice_{game_id}_rock"),
                InlineKeyboardButton("Ножницы", callback_data=f"choice_{game_id}_scissors"),
                InlineKeyboardButton("Бумага", callback_data=f"choice_{game_id}_paper")
            ]
        ])
    )

async def handle_player_choice(query, game_id):
    user_id = query.from_user.id
    choice = query.data.split("_")[2]
    games[game_id]["players"][user_id]["choice"] = choice
    
    players = games[game_id]["players"].values()
    if all(p["choice"] is not None for p in players):
        winner = determine_winner(players)
        await query.edit_message_text(
            text=winner,
            reply_markup=None
        )
        del games[game_id]

def determine_winner(players):
    p1, p2 = players
    beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
    
    if p1["choice"] == p2["choice"]:
        return f"🤝 Ничья!\n{p1['name']} и {p2['name']} выбрали {p1['choice']}"
    
    if beats[p1["choice"]] == p2["choice"]:
        return f"🏆 Победитель: {p1['name']}!\n{p1['choice']} бьет {p2['choice']}"
    return f"🏆 Победитель: {p2['name']}!\n{p2['choice']} бьет {p1['choice']}"

# Утилиты
def generate_email():
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=10))
    domain = random.choice(["1secmail.com", "1secmail.net", "1secmail.org"])
    return f"{name}@{domain}"

def get_emails(email):
    user, domain = email.split("@")
    response = requests.get(f"{TEMPMAIL_API}?action=getMessages&login={user}&domain={domain}")
    return response.json() if response.status_code == 200 else []

def create_text_result(title, content):
    return InlineQueryResultArticle(
        id=title[:64],
        title=title,
        input_message_content=InputTextMessageContent(content[:4096])
    )

def create_error_result():
    return create_text_result("⚠️ Ошибка", "Попробуйте позже")

# Запуск бота
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(InlineQueryHandler(inline_handler))
    app.add_handler(CallbackQueryHandler(game_callback, pattern="^(join|choice)_"))
    
    print("Бот запущен!")
    app.run_polling()
