import os
import discord
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('token')
DATABASE_HOST = os.getenv('host')
DATABASE_USER = os.getenv('user')
DATABASE_PASSWORD = os.getenv('password')
DATABASE_NAME = os.getenv('database')
GUILD_ID = int(os.getenv('guild_id'))
APPLICATION_ID = int(os.getenv('application_id'))

bot = commands.Bot(command_prefix='/', intents=discord.Intents.default())

db = mysql.connector.connect(
    host=DATABASE_HOST,
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
    database=DATABASE_NAME
)

cursor = db.cursor()

@bot.tree.command(name='hello', guild=discord.Object(id=GUILD_ID))
async def hello(interaction: discord.Interaction):
    await interaction.response.send(f'Hello, {interaction.user.mention}!')

@bot.tree.command(name='bye', guild=discord.Object(id=GUILD_ID))
async def bye(interaction: discord.Interaction):
    await interaction.response.send(f'Goodbye, {interaction.user.mention}!')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    guild = bot.get_guild(GUILD_ID)
    print(f'Connected to guild: {guild.name}')

bot.load_extension('commands')

bot.run(TOKEN)