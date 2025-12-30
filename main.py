import asyncio
import os

import discord
from dotenv import load_dotenv

from utils.madlib_manager import MadlibManager
from utils.remind_manager import ReminderManager
from utils.url_manager import AllowlistManager
from utils.rule_updater import update_rules_from_source

load_dotenv()
intents = discord.Intents.default()
intents.members = True
mentions = discord.AllowedMentions(everyone=False, users=True, roles=True, replied_user=True,)
bot = discord.Bot(intents=intents, allowed_mentions=mentions)

def get_token():
    environment = os.getenv('ENVIRONMENT')
    if environment == 'development':
        print("Running in Development Mode...")
        token = os.getenv('DEV_TOKEN')
    else:
        print("Running in Production Mode...")
        token = os.getenv('PROD_TOKEN')
    if not token:
        raise ValueError("Token not found! Check your .env file and environment setting.")
    return token

async def setup():
    try:
        print("Starting databases...")
        AllowlistManager()
        ReminderManager()
        MadlibManager()
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
    try:
        await update_rules_from_source()
    except Exception as e:
        print(f"An error occurred during rule update: {e}")
    try:
        bot.load_extensions('commands', recursive=True)
        print("Loading commands...")
    except Exception as e:
        print(f"Failed to load extensions: {e}")
    try:
        await bot.start(get_token())
    finally:
        if not bot.is_closed():
            print("Shutting down bot...")
            await bot.close()

@bot.event
async def on_ready():
    print(f'{bot.user} is now online and ready!')
    print('-----------------------------------------')

if __name__ == "__main__":
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        pass
