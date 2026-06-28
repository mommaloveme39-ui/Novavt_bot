import os
import logging
import requests
from flask import Flask, request
import telebot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token Initialization from Render Environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
AI_API_KEY = os.environ.get("AI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL") 

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def redirect_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **AI Assistant Bot**\n\n"
        "Send me any text prompt or question, and I will generate a response for you instantly using native processing."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_ai_request(message):
    user_prompt = message.text
    chat_id = message.chat.id
    
    bot.send_chat_action(chat_id, 'typing')
    
    # Direct internal API call - no external client libraries needed
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={AI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": user_prompt}]
        }],
        "systemInstruction": {
            "parts": [{"text": "You are a helpful, concise AI Telegram assistant. Keep your responses engaging and format them neatly using Markdown."}]
        },
        "generationConfig": {
            "maxOutputTokens": 800
        }
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=15)
        response_data = response.json()
        
        # Extract the text from the response structure safely
        ai_response = response_data['candidates'][0]['content']['parts'][0]['text']
        bot.reply_to(message, ai_response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing AI request: {e}")
        bot.reply_to(message, "⚠️ System is busy. Please try sending your message again.")

@app.route('/')
def index():
    return "Bot status: Active", 200

def set_webhook():
    if RENDER_EXTERNAL_URL and BOT_TOKEN:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.remove_webhook()
        success = bot.set_webhook(url=webhook_url)
        if success:
            logger.info(f"Webhook connected to: {webhook_url}")

set_webhook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
