from discord.ext import commands

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hello')
    async def hello(self, ctx):
        await ctx.send(f'Hello, {ctx.author.mention}!')

    @commands.command(name='bye')
    async def bye(self, ctx):
        await ctx.send(f'Goodbye, {ctx.author.mention}!')

def setup(bot):
    bot.add_cog(Commands(bot))