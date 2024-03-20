import sys
import os
import argparse
import base64
import json
from datetime import datetime
import pyotp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse, parse_qs

# Set up argument parser
#parser = argparse.ArgumentParser(description='Start a Telegram bot for generating HOTP tokens.')
#parser.add_argument('-t', '--token', help='Telegram Bot API Token', required=True)
#parser.add_argument('-i', '--otpauth', help='Initial otpauth URL', required=True)
#parser.add_argument('-p', '--password', help='Authentication', required=True)
#args = parser.parse_args()

# Load or initialize configuration
config_file = '.duo-telegram-bot.json'

token = os.getenv('TOKEN')
otpauth = os.getenv('OTPAUTH')
password = os.getenv('PASSWORD')

def load_or_init_config():
    try:
        with open(config_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        encrypted_otpauth = base64.b64encode(otpauth.encode('utf-8')).decode('utf-8')
        new_config = {'otpauth': encrypted_otpauth, 'counter': 0, 'logs': []}
        with open(config_file, 'w') as file:
            json.dump(new_config, file, indent=4)
        print(f"{datetime.now().isoformat()}: Created new configuration file '{config_file}'", file=sys.stderr)
        return new_config

config = load_or_init_config()

# Save configuration to file
def save_config():
    with open(config_file, 'w') as file:
        json.dump(config, file, indent=4)
        print(f"{datetime.now().isoformat()}: {config}", file=sys.stderr)

# Generate HOTP token
def generate_token():
    otpauth_decoded = base64.b64decode(config['otpauth']).decode('utf-8')
    url_parts = urlparse(otpauth_decoded)
    query_params = parse_qs(url_parts.query)
    secret = query_params['secret'][0]
    counter = config['counter']
    hotp = pyotp.HOTP(secret)
    token = hotp.at(counter)
    config['counter'] += 1  # Increment counter after generating token
    save_config()  # Save the updated counter to the config file
    print(f"{datetime.now().isoformat()}: Event logged.", file=sys.stderr)
    return token

# Asynchronous command handler function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hi! Send me a message containing "duo" and I will generate a HOTP token for you.')

# Asynchronous message handler function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if 'duo' in text.lower() and password in text:
        token = generate_token()
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'counter': config['counter'],
            'otpauth': config['otpauth'],
            'message': text
        }
        config['logs'].append(log_entry)
        save_config()
        await update.message.reply_text(f'本次的duo验证码是{token}')
    else:
        print(f"{datetime.now().isoformat()}: Received message: {text}, keyword not matached", file=sys.stderr)

# Main function to set up the application
def main():
    print(f"{datetime.now().isoformat()}: token:", token, file=sys.stderr)
    print(f"{datetime.now().isoformat()}: otpauth:", otpauth, file=sys.stderr)
    print(f"{datetime.now().isoformat()}: password:", password, file=sys.stderr)

    # Initialize the ApplicationBuilder with your bot token
    application = ApplicationBuilder().token(token).build()

    # Add the command handler to the application
    application.add_handler(CommandHandler("start", start))

    # Add the message handler to the application
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot in polling mode
    application.run_polling()

if __name__ == '__main__':
    main()