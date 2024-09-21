from discord import app_commands
from discord.interactions import Interaction

@app_commands.command(name="bonjour", description="Dire bonjour!")
async def bonjour(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'Bonjour, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")

@app_commands.command(name="bye", description="Dire au bye!")
async def bye(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'bye, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")