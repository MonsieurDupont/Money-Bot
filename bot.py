import discord
from discord.ext import commands
from settings import *
import asyncio
import logging
import sys
import traceback
from commands import *

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Création du bot
bot = commands.Bot(command_prefix="/", intents=intents)

# Gestion des erreurs globale
@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Une erreur s'est produite dans l'événement {event}")
    error_type, error_value, error_traceback = sys.exc_info()
    tb_lines = traceback.format_exception(error_type, error_value, error_traceback)
    logger.error(''.join(tb_lines))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Commande inconnue.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Il manque un argument requis pour cette commande.")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Une erreur s'est produite lors de l'exécution de la commande.")
        logger.error(f"Erreur lors de l'exécution de la commande {ctx.command}: {error}")
    else:
        await ctx.send("Une erreur inattendue s'est produite.")
        logger.error(f"Erreur inattendue: {error}")


@bot.event
async def on_ready():
    logger.info(f"Bot connecté en tant que {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synchronisé {len(synced)} commande(s)")
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation des commandes : {e}")

    logger.info("Commandes chargées :")
    commands = await bot.tree.fetch_commands()
    if commands:
        for command in commands:
            logger.info(f"- {command.name} ({command.description})")
    else:
        logger.warning("Aucune commande n'a été chargée.")

@bot.event
async def on_command(ctx):
    logger.info(f"Commande reçue : {ctx.command.name} ({ctx.command.description})")

@bot.event
async def on_command_completion(ctx):
    logger.info(f"Commande exécutée : {ctx.command.name} ({ctx.command.description})")

# Commande de test pour vérifier si les commandes sont correctement chargées
@bot.tree.command(name="test", description="Commande de test")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message("Test réussi!")

async def main():
    try:
        logger.info("Démarrage du bot...")
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.error("Échec de la connexion. Vérifiez le token.")
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors du démarrage du bot : {e}")
    finally:
        if bot.is_closed():
            logger.info("Connexion fermée. Le bot s'arrête.")

if __name__ == "__main__":
    setup_commands(bot)
    asyncio.run(main())