import discord
from discord.ext import commands
import os
import mysql.connector
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command prefix and intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with application ID from environment variables
bot = commands.Bot(command_prefix="!", intents=intents, application_id=int(os.getenv('APPLICATION_ID')))

# Database connection
try:
    conn = mysql.connector.connect(
        host=os.getenv('host'),
        user=os.getenv('user'),
        password=os.getenv('password'),
        database=os.getenv('database')
    )
    dbcursor = conn.cursor(buffered=True)
    logger.info("Connected to MySQL database")
except mysql.connector.Error as err:
    logger.error(f"Error connecting to MySQL database: {err}")
    exit(1)

# Event when the bot is ready
@bot.event
async def on_ready():
    logger.info(f'{bot.user} is connected to Discord!')
    guild = discord.Object(id=os.getenv('GUILD_ID'))
    try:
        await setup(bot)
        await bot.tree.sync(guild=guild)
        logger.info(f"Commands synced to guild {guild.id}")
    except discord.Forbidden:
        logger.error("Failed to sync commands: Forbidden")
    except discord.HTTPException as e:
        logger.error(f"Failed to sync commands: {e.status} {e.text}")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Async cog setup function
async def setup(bot: commands.Bot):
    guild = discord.Object(id=int(os.getenv('GUILD_ID')))
    await bot.tree.sync(guild=guild)

# Main bot function
async def main():
    async with bot:
        await setup(bot)
        try:
            await bot.start(os.getenv('TOKEN'))
        finally:
            dbcursor.close()
            conn.close()

