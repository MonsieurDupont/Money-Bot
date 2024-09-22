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


# Asynchronous cog loading (with 'await')
async def load_extensions():
    try:
        await bot.load_extension('commands')
    except Exception as e:
        print(f"Failed to load extension commands: {e}")


# Event when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} is connected to Discord!')
    try:
        guild_id = os.getenv('GUILD_ID')
        if guild_id:
            # Sync commands for the specific guild (faster updates)
            guild = discord.Object(id=guild_id)
            await bot.tree.sync(guild=guild)
            print(f"Commands synced for guild {guild_id}: {len(bot.tree.get_commands(guild=guild))} commands.")
        else:
            # Sync commands globally (slower to update, but no guild restriction)
            await bot.tree.sync()
            print(f"Commands globally synced: {len(bot.tree.get_commands())} commands.")

        # Debugging: Print registered commands after sync
        for cmd in bot.tree.get_commands():
            print(f"Registered command: {cmd.name}")

    except discord.Forbidden:
        print("Failed to sync commands: Forbidden")
    except discord.HTTPException as e:
        print(f"Failed to sync commands: {e.status} {e.text}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# Main bot function to run everything
async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv('TOKEN'))


# Run the main function
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
