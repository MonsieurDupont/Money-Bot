from discord import app_commands
from discord.ui import Button, View
from discord.interactions import Interaction

# Command /bonjour
@app_commands.command(name="bonjour", description="Say hello!")
async def bonjour(interaction: Interaction):
    try:
        await interaction.response.send_message(f'Hello, {interaction.user.mention}!')
    except Exception as e:
        print(f"Error: {e}")

# Command /bye with a button
@app_commands.command(name="bye", description="Say goodbye!")
async def bye(interaction: Interaction):
    button = Button(label='Test', style=discord.ButtonStyle.red)
    view = View()
    view.add_item(button)
    await interaction.response.send_message("Here's a button!", view=view)

# Function to set up commands and add them to the command tree
async def setup(bot):
    bot.tree.add_command(bonjour)
    bot.tree.add_command(bye)