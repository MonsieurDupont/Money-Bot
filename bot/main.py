import os
import discord
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Check if required environment variables are set
if not os.getenv('APPLICATION_ID') or not os.getenv('TOKEN') or not os.getenv('GUILD_ID'):
    print("Error: Required environment variables are not set")
    exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Command prefix and intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with application ID from environment variables
bot = commands.Bot(command_prefix="!", application_id=int(os.getenv('APPLICATION_ID')), intents=intents)

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
    guild = discord.Object(id=int(os.getenv('GUILD_ID')))
    try:
        await bot.tree.sync(guild=guild)
        logger.info(f"Commands synced to guild {guild.id}")
    except discord.Forbidden:
        logger.error("Failed to sync commands: Forbidden")
    except discord.HTTPException as e:
        logger.error(f"Failed to sync commands: {e.status} {e.text}")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Main bot function
async def main():
    async with bot:
        try:
            await bot.start(os.getenv('TOKEN'))
        except discord.LoginFailure:
            logger.error("Failed to login: Invalid token")
        except discord.HTTPException as e:
            logger.error(f"Failed to login: {e.status} {e.text}")
        except Exception as e:
            logger.error(f"Failed to login: {e}")
        finally:
            dbcursor.close()
            conn.close()

# Run the main function
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
    