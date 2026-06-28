import os
import logging
from flask import Flask, request
import telebot
from google import genai
from google.genai import types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token Initialization
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Provided automatically by Render

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
ai_client = genai.Client(api_key=GEMINI_API_KEY)
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
        "🤖 **Welcome to your AI Assistant Bot!**\n\n"
        "Send me any prompt, topic, or question, and I will generate high-quality text responses for you instantly."
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_ai_request(message):
    user_prompt = message.text
    chat_id = message.chat.id
    
    # Send a typing placeholder so the user knows the bot is processing
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        # Utilizing the recommended gemini-2.5-flash for fast text generation
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a helpful, concise AI Telegram assistant. Keep your responses engaging and format them neatly using Markdown.",
                max_output_tokens=800,
            )
        )
        
        bot.reply_to(message, response.text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        bot.reply_to(message, "⚠️ Sorry, I ran into an error processing that request. Please try again.")

@app.route('/')
def index():
    return "Bot is running live.", 200

def set_webhook():
    if RENDER_EXTERNAL_URL and BOT_TOKEN:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{BOT_TOKEN}"
        bot.remove_webhook()
        success = bot.set_webhook(url=webhook_url)
        if success:
            logger.info(f"Webhook successfully set to: {webhook_url}")
        else:
            logger.error("Failed to set webhook.")

# Set webhook immediately on startup
set_webhook()

if __name__ == "__main__":
    # Local fallback
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
