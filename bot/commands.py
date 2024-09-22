from discord import app_commands
from discord.ui import Button, View
from discord.interactions import Interaction

# Commande /bonjour
@app_commands.command(name="bonjour", description="Dire bonjour!")
async def bonjour(interaction: Interaction):
    try:
        await interaction.response.send_message(f'Bonjour, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")

# Commande /bye avec un bouton
@app_commands.command(name="bye", description="Dire au revoir!")
async def bye(interaction: Interaction):
    button = Button(label='Test', style=discord.ButtonStyle.red)
    view = View()
    view.add_item(button)
    await interaction.response.send_message("Voici un bouton !", view=view)

# Fonction pour configurer les commandes et les ajouter à la commande d'arborescence (tree)
async def setup(bot):
    bot.tree.add_command(bonjour)
    bot.tree.add_command(bye)