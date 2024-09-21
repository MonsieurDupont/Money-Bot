import os
import discord
from dotenv import load_dotenv
from discord import *

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# DOTENV
load_dotenv()
TOKEN = os.getenv('TOKEN')

client = discord.Client(intents=intents)

@client.event
async def on_ready():
  print(f'{client.user} est connecté !')
  try:
      synced = await bot.tree.sync()
      print(f"{len(synced)} commande(s) synchronisée(s)")
  except Exception as exep:
      print(exep)

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  if message.content.startswith('bonjour'):
    await message.channel.send('Bonjour !')

  if message.content.startswith('idir'):
    await message.channel.send('ANINI')

# LOGIN
client.run(token=TOKEN) 