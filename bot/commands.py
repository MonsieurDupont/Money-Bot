from discord import app_commands, Interaction
from discord.ui import Button, View
from main import bot

# Define commands
bonjour_command = app_commands.Command(name="bonjour", description="Say hello!")
async def bonjour(interaction: Interaction):
    await interaction.response.send_message(f'Bonjour {interaction.user.mention}!')

<<<<<<< HEAD
bye_command = app_commands.Command(name="bye", description="Say goodbye!")
async def bye(interaction: Interaction):
    button = Button(label="Click Me!", style=discord.ButtonStyle.green)
=======
@app_commands.command(name="bye", description="Say goodbye!")
async def bye_command(interaction: Interaction):
    button = Button(label="Click Me!")
>>>>>>> 39aa10ade41010c4218248cbdf0424530722757e

    # Define button callback
    async def button_callback(interaction: Interaction):
        await interaction.response.send_message("Button clicked!")

    button.callback = button_callback  # Assign the callback to the button

    view = View()
    view.add_item(button)

    try:
        await interaction.response.send_message(f'Bye {interaction.user.mention}!', view=view)
    except Exception as e:
        print(f"COMMAND ERROR: {e}")  # Print the error to the console

# Add commands to bot.tree
bot.tree.add_command(bonjour_command)
bot.tree.add_command(bye_command)