from discord import app_commands
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
class MyView(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View
    @discord.ui.button(label="Click me!", style=discord.ButtonStyle.primary, emoji="😎") # Create a button with the label "😎 Click me!" with color Blurple
    async def button_callback(self, button, interaction):
        await interaction.response.send_message("You clicked the button!") # Send a message when the button is clicked

@app_commands.command(name="bye", description="Dire au bye!")
async def button(ctx):
    await ctx.respond("This is a button!", view=MyView()) # Send a message with our View class that contains the button       