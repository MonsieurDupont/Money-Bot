import discord
import os
import mysql.connector
import discord.app_commands as app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# Définir l'objet bot avec le préfixe de commande
intents = discord.Intents.default()
intents.message_content = True  # Assurez-vous d'avoir les bons intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Connexion à la base de données
try:
    conn = mysql.connector.connect(
        host=os.getenv('host'),
        user=os.getenv('user'),
        password=os.getenv('password'),
        database=os.getenv('database')
    )
    dbcursor = conn.cursor(buffered=True)
    print("Connecté à la base de données MySQL")
except mysql.connector.Error as err:
    print(f"Erreur de connexion à la base de données MySQL: {err}")
    exit(1)

# Événement lorsque le bot est prêt
@bot.event
async def on_ready():
    print(f'{bot.user} a connecté à Discord!')
    await bot.tree.sync()  # Synchroniser les commandes avec Discord

# Charger les extensions
bot.load_extension('commands')
bot.load_extension('games')

# Démarrer le bot en utilisant le token dans .env
bot.run(os.getenv('TOKEN'))