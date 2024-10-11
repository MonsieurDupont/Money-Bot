import discord
from discord.ext import commands
from settings import *
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix="/", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print("Bot prêt")
    try:
        await bot.tree.sync()
    except discord.HTTPException as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")
        await bot.close()
        return

    print("Commandes chargées :")
    commands_loaded = False
    for command in bot.tree.commands:
        print(f"- {command.name} ({command.description})")
        commands_loaded = True

    if not commands_loaded:
        print("Erreur : aucune commande n'a été chargée.")
        if not os.path.exists("commands.py"):
            print("Erreur : le fichier commands.py n'existe pas.")
        elif not os.path.isfile("commands.py"):
            print("Erreur : le fichier commands.py n'est pas un fichier.")
        else:
            print("Erreur : les commandes ne sont pas correctement définies dans le fichier commands.py")
        await bot.close()
        return

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Commande inconnue.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Il manque un argument requis pour cette commande.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Erreur lors de l'exécution de la commande.")
    else:
        await ctx.send("Erreur inconnue.")
        logging.error(f"Erreur inconnue : {error}")

@bot.event
async def on_command(ctx):
    print(f"Commande reçue : {ctx.command.name} ({ctx.command.description})")

@bot.event
async def on_command_completion(ctx):
    print(f"Commande exécutée : {ctx.command.name} ({ctx.command.description})")

async def main():
    try:
        await bot.start(TOKEN)
    except discord.HTTPException as e:
        print(f"Erreur lors de la connexion au serveur Discord : {e}")
    except Exception as e:
        print(f"Erreur inconnue : {e}")

asyncio.run(main())