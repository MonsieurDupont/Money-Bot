import discord
from discord.ext import commands
from discord.interactions import Interaction
from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

# Registering the slash command correctly using app_commands
@bot.tree.command(name="hello", description="Say hello!")
async def hello(interaction: Interaction):
    try:
        # Responding properly to the interaction using send_message
        await interaction.response.send_message(f'Hello, {interaction.user.mention}!')
    except Exception as e:
        print(f"Error: {e}")

bot.run(os.getenv('TOKEN'))
