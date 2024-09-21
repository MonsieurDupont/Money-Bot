import discord

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

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

client.run('MTI4NzAxNjEyMjQ0MDIyNDc2OA.GfNXGv.cDs1KAC_aKhdBsD7mpuAMhza7nPZWW5qoIuVyI')