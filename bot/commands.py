from discord import app_commands
from discord.ui import Button, View
from discord.interactions import Interaction

@app_commands.command(name="bonjour", description="Dire bonjour!")
async def bonjour(interaction: Interaction):
    try:
        await interaction.response.send_message(f'Bonjour, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")

@app_commands.command(name="bye", description="Dire au revoir!")
async def bye(interaction: Interaction):
    button = Button(label='Test', style=discord.ButtonStyle.red)
    view = View()
    view.add_item(button)
    await interaction.response.send_message("Voici un bouton !", view=view)