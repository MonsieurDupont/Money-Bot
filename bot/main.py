import discord
import os
import mysql.connector
import discord.app_commands as app_commands
from discord.ext import commands
from dotenv import load_dotenv
from commands import bonjour, bye

load_dotenv()

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

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} a connecté à Discord!')
    await bot.tree.sync()

bot.tree.add_command(app_commands.Command(name="bonjour", description="Dire bonjour!", func=bonjour))
bot.tree.add_command(app_commands.Command(name="bye", description="Dire au bye!", func=bye))

bot.run(os.getenv('TOKEN'))