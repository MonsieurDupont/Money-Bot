import os
import configparser
import mysql.connector
import discord
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load settings from settings.ini file
commandsconfig = configparser.ConfigParser()
commandsconfig.read('settings.ini')

# Define constants
TOKEN = os.getenv("TOKEN")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
PASSWORD = os.getenv("PASSWORD")
DATABASE = os.getenv("DATABASE")
GUILD_ID = os.getenv("GUILD_ID")
APPLICATION_ID = os.getenv("APPLICATION_ID")
CoinEmoji = "<:AploucheCoin:1286080674046152724>"

if 'Constants' in commandsconfig:
    min_work_pay = commandsconfig.getint('Constants', 'min_pay')
    max_work_pay = commandsconfig.getint('Constants', 'max_pay')
    work_cooldown_time = commandsconfig.getint('Constants', 'work_cooldown')
    print(f"Succesfully read {len(commandsconfig.options('Constants'))} 'Constants' in 'settings.ini.'")
else:
    print("Cannot find 'Constants' in settings.ini")

# Define colors
color_green = 0x98d444
color_blue = 0x448ad4
color_red = 0xd44e44

# Define database tables and fields
TABLE_USERS = "users"
TABLE_TRANSACTIONS = "transactions"
FIELD_USER_ID = "user_id"
FIELD_CASH = "cash"
FIELD_BANK = "bank"
FIELD_TYPE = "type"
FIELD_TIMESTAMP = "timestamp"
FIELD_AMOUNT = "amount"

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

print("Fin de l'exécution de settings.py")