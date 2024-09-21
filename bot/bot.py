import discord
from discord.ext import commands
from discord.interactions import Interaction

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await bot.tree.sync()

@bot.tree.command(name="hello", description="Say hello!")
async def hello(interaction: Interaction):
    await interaction.response.send_message(f'Hello, {interaction.user.mention}!')

bot.run('')