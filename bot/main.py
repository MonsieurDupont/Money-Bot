import discord
from discord.ext import commands
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Command prefix
intents = discord.Intents.default()
intents.message_content = True
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

# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} is connected to Discord!')
    guild = discord.Object(id=os.getenv('GUILD_ID'))
    try:
        await bot.tree.sync(guild=guild)
        print(f"Commands synced to guild {guild.id}")
    except discord.Forbidden:
        print("Failed to sync commands: Forbidden")
    except discord.HTTPException as e:
        print(f"Failed to sync commands: {e.status} {e.text}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Async cog setup function
async def setup(bot: commands.Bot):
    await bot.tree.copy_global_to(guild=discord.Object(id=os.getenv('GUILD_ID')))

# Main bot function
async def main():
    async with bot:
        await setup(bot)
        await bot.start(os.getenv('TOKEN'))

# Run the main function
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())