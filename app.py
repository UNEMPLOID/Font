import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, Filters, MessageHandler
from PIL import Image, ImageDraw, ImageFont
import os
import requests
import random
import datetime
import pytz
from googletrans import Translator
from forex_python.converter import CurrencyRates
import schedule
import time

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Paths to fonts and stickers
FONTS_DIR = "fonts"
STICKERS_DIR = "stickers"

# Bot owner ID
OWNER_ID = 5460343986

# Channels and group to join
REQUIRED_CHANNELS = ['@Found_Us', '@Falcon_Security']
REQUIRED_GROUP = '@Indian_Hacker_Group'

# Store user and chat data
users = set()
chats = set()

# Initialize APIs
translator = Translator()
currency_converter = CurrencyRates()

# API Keys
WEATHER_API_KEY = "680b3c5d37f04142945153351240807"
USDA_API_KEY = "feDih4wy8AVem2htlnHhidL5ODSZFfAZ9WmudwBT"

# Load available fonts
def load_fonts():
    return {os.path.splitext(f)[0]: f for f in os.listdir(FONTS_DIR) if f.endswith('.ttf') or f.endswith('.otf')}

# Check if user is a member of required channels and group
def check_membership(user_id):
    try:
        for channel in REQUIRED_CHANNELS:
            status = requests.get(f'https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={channel}&user_id={user_id}').json()
            if status['result']['status'] not in ['member', 'administrator', 'creator']:
                return False
        status = requests.get(f'https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={REQUIRED_GROUP}&user_id={user_id}').json()
        if status['result']['status'] not in ['member', 'administrator', 'creator']:
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    try:
        users.add(update.message.from_user.id)
        chats.add(update.message.chat_id)
        update.message.reply_text('Hi! Use /help to see all available commands.')
    except Exception as e:
        logger.error(f"Error in start command: {e}")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    try:
        help_text = (
            "Available commands:\n"
            "/font <text>: Display text in different fonts.\n"
            "/broadcast <message>: Broadcast a message to all users.\n"
            "/weather <city>: Get weather information.\n"
            "/check_membership: Check membership status.\n"
            "/recipe <dish>: Get a recipe suggestion.\n"
            "/fitness_tip: Get a fitness tip.\n"
            "/currency <amount> <from_currency> to <to_currency>: Convert currency.\n"
            "/schedule_event <date> <time> <event_description>: Schedule an event.\n"
            "/learn <topic>: Access learning modules.\n"
            "/poll <question>: Create a poll.\n"
            "/news: Get the latest news.\n"
            "/set_reminder <time> <reminder_message>: Set a reminder.\n"
            "/stats: Show bot usage statistics."
        )
        update.message.reply_text(help_text)
    except Exception as e:
        logger.error(f"Error in help command: {e}")

def font_command(update: Update, context: CallbackContext) -> None:
    """Display the text in all available fonts."""
    try:
        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text('Please provide text to display in fonts. Usage: /font <text>')
            return
        
        text = update.message.text.split(' ', 1)[1]
        fonts = load_fonts()
        keyboard = [
            [InlineKeyboardButton(font_name, callback_data=f"font_{font_file}_{text}")]
            for font_name, font_file in fonts.items()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Here are your text in different fonts:', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in font command: {e}")

def button(update: Update, context: CallbackContext) -> None:
    """Handle button presses."""
    try:
        query = update.callback_query
        query.answer()

        data = query.data.split('_')
        if data[0] == 'font':
            font_file, text = data[1], '_'.join(data[2:])
            img = convert_to_font(text, font_file)
            img_path = os.path.join(STICKERS_DIR, "output.png")
            img.save(img_path)
            with open(img_path, 'rb') as f:
                query.message.reply_photo(f)
        elif data[0] == 'check':
            if check_membership(query.from_user.id):
                query.edit_message_text("You have successfully joined the required channels and group.")
            else:
                query.edit_message_text("Please join all the required channels and group to use the bot.")
    except Exception as e:
        logger.error(f"Error in button handler: {e}")

def convert_to_font(text, font_path):
    """Convert text to an image with a fashionable font."""
    try:
        img = Image.new('RGB', (400, 100), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(os.path.join(FONTS_DIR, font_path), 40)
        d.text((10, 10), text, font=font, fill=(0, 0, 0))
        return img
    except Exception as e:
        logger.error(f"Error in convert_to_font: {e}")

def broadcast(update: Update, context: CallbackContext) -> None:
    """Broadcast a message to all users."""
    try:
        if update.message.from_user.id != OWNER_ID:
            update.message.reply_text("You are not authorized to use this command.")
            return

        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text("Please provide a message to broadcast. Usage: /broadcast <message>")
            return

        message = update.message.text.split(' ', 1)[1]
        successful_sends = 0
        for user_id in users:
            try:
                context.bot.send_message(chat_id=user_id, text=message)
                successful_sends += 1
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
        update.message.reply_text(f"Broadcast message sent to {successful_sends} users.")
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")

def weather(update: Update, context: CallbackContext) -> None:
    """Fetch and display weather information."""
    try:
        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text('Please provide a city name. Usage: /weather <city>')
            return

        city = update.message.text.split(' ', 1)[1]
        api_key = WEATHER_API_KEY
        weather_url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}&aqi=no"
        response = requests.get(weather_url).json()

        if 'error' not in response:
            location = response['location']
            current = response['current']
            weather_info = (
                f"Weather in {location['name']}, {location['region']}, {location['country']}:\n"
                f"Temperature: {current['temp_c']}°C\n"
                f"Condition: {current['condition']['text']}\n"
                f"Humidity: {current['humidity']}%\n"
                f"Wind Speed: {current['wind_kph']} kph\n"
            )
            update.message.reply_text(weather_info)
        else:
            update.message.reply_text(f"Could not find weather data for {city}.")
    except Exception as e:
        logger.error(f"Error in weather command: {e}")

def recipe(update: Update, context: CallbackContext) -> None:
    """Get a recipe suggestion based on the dish provided."""
    try:
        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text('Please provide a dish name. Usage: /recipe <dish>')
            return

        dish = update.message.text.split(' ', 1)[1]
        api_key = USDA_API_KEY
        recipe_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={dish}&api_key={api_key}&pageSize=1"
        response = requests.get(recipe_url).json()

        if 'foods' in response and response['foods']:
            food = response['foods'][0]
            recipe_info = (
                f"Recipe for {food['description']}:\n"
                f"Nutritional Info:\n"
                f"Calories: {food['foodNutrients'][3]['value']} kcal\n"
                f"Protein: {food['foodNutrients'][0]['value']} g\n"
                f"Fat: {food['foodNutrients'][1]['value']} g\n"
                f"Carbohydrates: {food['foodNutrients'][2]['value']} g\n"
            )
            update.message.reply_text(recipe_info)
        else:
            update.message.reply_text(f"No recipe found for {dish}.")
    except Exception as e:
        logger.error(f"Error in recipe command: {e}")

def fitness_tip(update: Update, context: CallbackContext) -> None:
    """Provide a random fitness tip."""
    try:
        tips = [
            "Remember to stay hydrated!",
            "Take the stairs instead of the elevator.",
            "Stretch before and after exercising to prevent injury.",
            "Try to get at least 30 minutes of exercise every day.",
            "Balanced diet is key to staying fit."
        ]
        update.message.reply_text(random.choice(tips))
    except Exception as e:
        logger.error(f"Error in fitness_tip command: {e}")

def currency(update: Update, context: CallbackContext) -> None:
    """Convert currency based on user input."""
    try:
        if len(update.message.text.split(' ')) < 4:
            update.message.reply_text('Usage: /currency <amount> <from_currency> to <to_currency>')
            return

        _, amount, from_currency, _, to_currency = update.message.text.split()
        amount = float(amount)
        result = currency_converter.convert(from_currency.upper(), to_currency.upper(), amount)
        update.message.reply_text(f"{amount} {from_currency} = {result:.2f} {to_currency}")
    except Exception as e:
        logger.error(f"Error in currency command: {e}")
        update.message.reply_text(f"Error: {e}")

def schedule_event(update: Update, context: CallbackContext) -> None:
    """Schedule an event."""
    try:
        if len(update.message.text.split(' ')) < 4:
            update.message.reply_text('Please provide date, time, and event description. Usage: /schedule_event <date> <time> <event_description>')
            return

        inputs = update.message.text.split(' ', 3)
        date = inputs[1]
        time = inputs[2]
        event_description = inputs[3]
        
        scheduled_time = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        local_tz = pytz.timezone('Asia/Kolkata')  # Change to appropriate timezone
        scheduled_time = local_tz.localize(scheduled_time)
        
        schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(send_event_reminder, context.bot, update.message.chat_id, event_description)
        
        update.message.reply_text(f"Event scheduled successfully: {event_description}")
    except Exception as e:
        logger.error(f"Error in schedule_event command: {e}")
        update.message.reply_text(f"Error: {e}")

def send_event_reminder(bot: Bot, chat_id: int, event_description: str) -> None:
    """Send event reminder."""
    try:
        bot.send_message(chat_id=chat_id, text=f"Reminder: {event_description}")
    except Exception as e:
        logger.error(f"Error in send_event_reminder: {e}")

def learn(update: Update, context: CallbackContext) -> None:
    """Provide learning modules based on user input."""
    try:
        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text('Please provide a topic to learn. Usage: /learn <topic>')
            return

        topic = update.message.text.split(' ', 1)[1]
        # Implement learning module fetching based on topic
        update.message.reply_text(f"Here are learning modules on {topic}.")
    except Exception as e:
        logger.error(f"Error in learn command: {e}")

def poll(update: Update, context: CallbackContext) -> None:
    """Create a poll based on user input."""
    try:
        if len(update.message.text.split(' ')) < 2:
            update.message.reply_text('Please provide a question for the poll. Usage: /poll <question>')
            return

        question = update.message.text.split(' ', 1)[1]
        # Implement poll creation
        options = ["Option 1", "Option 2", "Option 3"]  # Example options
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(option, callback_data=f"poll_{question}_{option}")]
            for option in options
        ])
        update.message.reply_text(f"Poll: {question}", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in poll command: {e}")

def news(update: Update, context: CallbackContext) -> None:
    """Get the latest news."""
    try:
        # Implement news fetching from a news API
        news_headline = "Example News Headline"
        news_link = "https://example.com"
        news_text = f"📰 {news_headline}\nRead more: {news_link}"
        update.message.reply_text(news_text)
    except Exception as e:
        logger.error(f"Error in news command: {e}")

def set_reminder(update: Update, context: CallbackContext) -> None:
    """Set a reminder based on user input."""
    try:
        if len(update.message.text.split(' ')) < 3:
            update.message.reply_text('Please provide time and reminder message. Usage: /set_reminder <time> <reminder_message>')
            return

        inputs = update.message.text.split(' ', 2)
        time_str = inputs[1]
        reminder_message = inputs[2]
        
        scheduled_time = datetime.datetime.strptime(time_str, "%H:%M")
        local_tz = pytz.timezone('Asia/Kolkata')  # Change to appropriate timezone
        scheduled_time = local_tz.localize(scheduled_time)
        
        schedule.every().day.at(scheduled_time.strftime("%H:%M")).do(send_reminder, context.bot, update.message.chat_id, reminder_message)
        
        update.message.reply_text(f"Reminder set successfully: {reminder_message}")
    except Exception as e:
        logger.error(f"Error in set_reminder command: {e}")
        update.message.reply_text(f"Error: {e}")

def send_reminder(bot: Bot, chat_id: int, reminder_message: str) -> None:
    """Send reminder."""
    try:
        bot.send_message(chat_id=chat_id, text=f"Reminder: {reminder_message}")
    except Exception as e:
        logger.error(f"Error in send_reminder: {e}")

def automatic_messages() -> None:
    """Send automatic messages like quotes, jokes, and fun facts."""
    try:
        schedule.every().day.at("09:00").do(send_daily_message)
    except Exception as e:
        logger.error(f"Error in automatic_messages: {e}")

def send_daily_message() -> None:
    """Send a random message (quote, joke, or fun fact)."""
    try:
        messages = [
            "Quote of the Day: Success is not final, failure is not fatal: It is the courage to continue that counts.",
            "Joke of the Day: Why don't scientists trust atoms? Because they make up everything!",
            "Fun Fact of the Day: Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible."
        ]
        message = random.choice(messages)
        for chat_id in chats:
            context.bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.error(f"Error in send_daily_message: {e}")

def stats(update: Update, context: CallbackContext) -> None:
    """Show bot usage statistics."""
    try:
        user_count = len(users)
        chat_count = len(chats)
        update.message.reply_text(f"Bot usage statistics:\n- Users: {user_count}\n- Chats: {chat_count}")
    except Exception as e:
        logger.error(f"Error in stats command: {e}")

def main() -> None:
    """Start the bot."""
    try:
        global TOKEN
        # Replace ' with your bot's API token
        TOKEN = "6945433492:AAGZIXcoiDprhlZKSVId3tjqg5HF-XTnSc0"
        updater = Updater(TOKEN)

        dispatcher = updater.dispatcher

        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CommandHandler("font", font_command))
        dispatcher.add_handler(CommandHandler("broadcast", broadcast))
        dispatcher.add_handler(CommandHandler("weather", weather))
        dispatcher.add_handler(CommandHandler("recipe", recipe))
        dispatcher.add_handler(CommandHandler("fitness_tip", fitness_tip))
        dispatcher.add_handler(CommandHandler("currency", currency))
        dispatcher.add_handler(CommandHandler("schedule_event", schedule_event))
        dispatcher.add_handler(CommandHandler("learn", learn))
        dispatcher.add_handler(CommandHandler("poll", poll))
        dispatcher.add_handler(CommandHandler("news", news))
        dispatcher.add_handler(CommandHandler("set_reminder", set_reminder))
        dispatcher.add_handler(CommandHandler("stats", stats))
        dispatcher.add_handler(CallbackQueryHandler(button))

        # Only handle commands and ignore all other messages
        dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), lambda update, context: None))

        # Schedule automatic messages
        automatic_messages()

        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"Error in main function: {e}")

if __name__ == '__main__':
    main()
