from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import Button, View

bot_commands = []


@app_commands.command(name="bonjour", description="Say hello!")
async def bonjour(interaction: Interaction):
    await interaction.response.send_message(f'Bonjour {interaction.user.mention}!')


bot_commands.append(bonjour)


@app_commands.command(name="bye", description="Say goodbye!")
async def bye_command(interaction: Interaction):
    button = Button(label="Click Me!", style=discord.ButtonStyle.green)

    # Define button callback
    async def button_callback(interaction: Interaction):
        await interaction.response.send_message("Button clicked!")

    button.callback = button_callback  # Assign the callback to the button

    view = View()
    view.add_item(button)

    try:
        await interaction.response.send_message(f'Bye {interaction.user.mention}!', view=view)
    except Exception as e:
        print(f"COMMAND ERROR: {e}")


bot_commands.append(bye_command)


# Setup function for command registration
async def setup(bot: commands.Bot):
    for command in bot_commands:
        bot.tree.add_command(command)