from discord import app_commands
from discord.ui import Button, View
from discord.interactions import Interaction

@app_commands.command(name="bonjour", description="Dire bonjour!")
async def bonjour(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'Bonjour, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")

""" @app_commands.command(name="bye", description="Dire au bye!")
async def bye(interaction: Interaction):
    try:
        # Répondre correctement à l'interaction en utilisant send_message
        await interaction.response.send_message(f'bye, {interaction.user.mention}!')
    except Exception as e:
        print(f"Erreur: {e}")
 """

@app_commands.command(name="bye", description="Dire au bye!")
async def button(ctx):
    button = Button(label='test', style=discord.ButtonStyle.red)
    View = View()
    view.add_item(button)
    await ctx.send("This is a button!", view=View) # Send a message with our View class that contains the button       