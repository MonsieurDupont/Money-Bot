import discord
import os
import mysql.connector
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

dbcursor.execute("CREATE TABLE IF NOT EXISTS player_stats (player VARCHAR(255), cash int, bank int)")
dbcursor.execute("SHOW TABLES")
for x in dbcursor: 
    print(x)
# Événement lorsque le bot est prêt
@bot.event
async def on_ready():
    print(f'{bot.user} est connecté à Discord!')
    try:
        await bot.tree.sync()  # Synchroniser les commandes avec Discord
    except Exception as e:
        print(f"Erreur de synchronisation des commandes : {e}")

# Fonction pour charger les extensions
""" async def load_extensions():
    await bot.load_extension('commands')
    await bot.load_extension('games') """

# Charger les extensions au démarrage du bot
""" @bot.event
async def on_ready():
    print(f'{bot.user} est connecté à Discord!')
    # await load_extensions()
    try:
        synced = await bot.tree.sync()
        print(f"Commandes synchronisées: {len(synced)} commandes.")
    except Exception as e:
        print(f"Erreur de synchronisation des commandes : {e}") """

# Démarrer le bot en utilisant le token dans .env
bot.run(os.getenv('TOKEN'))