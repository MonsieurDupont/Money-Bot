from discord import app_commands
from discord.interactions import Interaction

async def bonjour_func(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'Bonjour, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")

async def bye_func(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'bye, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")