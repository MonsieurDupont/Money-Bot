import discord 
import mysql.connector
from discord.ext import commands
from discord.interactions import Interaction
from dotenv import load_dotenv
import os

load_dotenv()

conn = mysql.connector.connect(host=os.getenv('host'),user=os.getenv('user'),password=os.getenv('password'),database=os.getenv('database'))
conn.commit = True
dbcursor = conn.cursor(buffered=True)


intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

@bot.tree.command(name="hello", description="Say hello!")
async def hello(interaction: Interaction):
    await interaction.followup.send(f'Hello, {interaction.user.mention}!')

bot.run(os.getenv('TOKEN'))