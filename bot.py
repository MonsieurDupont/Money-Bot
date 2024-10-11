import discord
from discord.ext import commands
from settings import *
import asyncio

bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

async def main():
    await bot.start(TOKEN)

asyncio.run(main())