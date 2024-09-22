from discord import app_commands
from discord.ui import Button, View
from discord.interactions import Interaction

# Command /bonjour
bonjour = app_commands.Command(name="bonjour", description="Say hello!")
async def bonjour_callback(interaction: Interaction):
    try:
        await interaction.response.send_message(f'Hello, {interaction.user.mention}!')
    except Exception as e:
        print(f"Error: {e}")

# Command /bye with a button
bye = app_commands.Command(name="bye", description="Say goodbye!")
async def bye_callback(interaction: Interaction):
    button = Button(label='Test', style=discord.ButtonStyle.red)
    view = View()
    view.add_item(button)
    await interaction.response.send_message("Here's a button!", view=view)

# Function to set up commands and add them to the command tree
async def setup(bot):
    bot.tree.add_command(bonjour)
    bot.tree.add_command(bye)