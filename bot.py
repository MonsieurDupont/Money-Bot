import discord
from discord.ext import commands
from settings import *
import asyncio

bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    await bot.tree.sync()
    print("Commandes chargées :")
    for command in bot.tree.commands:
        print(f"- {command.name} ({command.description})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Commande inconnue.")
    else:
        await ctx.send("Erreur lors de l'exécution de la commande.")
@bot.event
async def on_command(ctx):
    print(f"Commande reçue : {ctx.command.name} ({ctx.command.description})")

@bot.event
async def on_command_completion(ctx):
    print(f"Commande exécutée : {ctx.command.name} ({ctx.command.description})")

async def main():
    await bot.start(TOKEN)

asyncio.run(main())