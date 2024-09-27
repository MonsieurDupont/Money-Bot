import discord
import os
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
import asyncio
from commands import setup

load_dotenv()

TOKEN = os.getenv('token')
GUILD_ID = int(os.getenv('guild_id'))

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {'options' : '-vn'}
YDL_OPTIONS = {'format' : 'bestaudio', 'noplaylist' : True}

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        await ctx.send('mets ton doigt dans mon cul')
        try:
            await voice_channel.connect()
        except Exception as e:
            print({voice_channel})


    
    async def play_next(self, ctx):
        if self.queue:
            url, title = self.queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda _:self.client.loop.create_task(self.play_next(ctx)))
            await ctx.send(f'**{title}**')
        elif not ctx.voice_client.is_plauing():
            await ctx.send("La file est vide")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send('Musique passée')

client = commands.Bot(command_prefix='!', intents=intents)

async def main():
    await client.add_cog(MusicBot(client))
    await client.start(TOKEN)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    guild = client.get_guild(GUILD_ID)
    if guild is not None:
        print(f'Connected to guild: {guild.name}')
    else:
        print(f'Failed to connect to guild with ID {GUILD_ID}')

    try:
        await setup(client)
    except Exception as e:
        print(f'Failed to load extension: {e}')

asyncio.run(main())

