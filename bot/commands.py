from discord.ext import commands
from discord import app_commands, Interaction

class BotCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="bonjour", description="Say hello!")
    async def bonjour(self, interaction: Interaction):
        await interaction.response.send_message(f'Bonjour {interaction.user.mention}!')

    @app_commands.command(name="bye", description="Say goodbye!")
    async def bye_command(self, interaction: Interaction):
        await interaction.response.send_message(f'Bye {interaction.user.mention}!')

# Required setup function for cogs
async def setup(bot: commands.Bot):
    await bot.add_cog(BotCommands(bot))
