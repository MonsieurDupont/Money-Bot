import discord
from discord.ext import commands
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Define the bot with the command prefix
intents = discord.Intents.default()
intents.message_content = True  # Make sure to have the correct intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Database connection
try:
    conn = mysql.connector.connect(
        host=os.getenv('host'),
        user=os.getenv('user'),
        password=os.getenv('password'),
        database=os.getenv('database')
    )
    dbcursor = conn.cursor(buffered=True)
    print("Connected to MySQL database")
except mysql.connector.Error as err:
    print(f"Error connecting to MySQL database: {err}")
    exit(1)

# Load extensions
bot.load_extension('commands')

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} is connected to Discord!')
    await bot.tree.sync(guild=discord.Object(id=os.getenv('GUILD_ID')))  # Replace GUILD_ID with your guild ID
    print(f"Commands synced: {len(bot.tree.get_commands())} commands.")

# Run the bot with the token from .env
bot.run(os.getenv('TOKEN'))