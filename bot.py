import discord
from discord.ext import commands
from settings import *
import asyncio

bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Commande inconnue.")
    else:
        await ctx.send("Erreur lors de l'exécution de la commande.")

async def main():
    await bot.start(TOKEN)

asyncio.run(main())