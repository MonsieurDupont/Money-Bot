from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import Button, View

class BotCommands(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="bonjour", description="Say hello!")
    async def bonjour(self, interaction: Interaction):
        try:
            await interaction.response.send_message(f'Hello, {interaction.user.mention}!')
        except Exception as e:
            print(f"Error: {e}")

    @app_commands.command(name="bye", description="Say goodbye!")
    async def bye(self, interaction: Interaction):
        button = Button(label='Test', style=discord.ButtonStyle.red)
        button.callback = self.button_callback
        view = View()
        view.add_item(button)
        await interaction.response.send_message("Here's a button!", view=view)

    async def button_callback(self, interaction: Interaction):
        await interaction.response.send_message("Button clicked!")

async def setup(bot):

    bot.tree.add_command(BotCommands(bot))