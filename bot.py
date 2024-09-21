import os
from dotenv import load_dotenv
import discord
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

load_dotenv()
TOKEN = os.getenv('TOKEN')
print(TOKEN)

""" client = discord.Client(intents=intents)

@client.event
async def on_ready():
  print(f'{client.user} est connecté !')

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  if message.content.startswith('bonjour'):
    await message.channel.send('Bonjour !')

  if message.content.startswith('idir'):
    await message.channel.send('ANINI')

# LOGIN
client.run(token=TOKEN) """