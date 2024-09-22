from discord.ext import commands
from discord import app_commands

class MyCommands(app_commands.Group):
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
        view = View()
        view.add_item(button)
        await interaction.response.send_message("Here's a button!", view=view)

async def setup(bot):
    my_commands = MyCommands(bot)
    bot.tree.add_command(my_commands)