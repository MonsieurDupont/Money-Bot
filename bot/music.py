import discord
import os
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv
import asyncio

load_dotenv()

TOKEN = os.getenv('token')

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
        if not voice_channel:
            return await ctx.send("Rejoins un vocal fdp")
        if not ctx.voice_client:
            await voice_channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url=f"ytsearch:{search}", download=False)
                if 'entries' in info:
                    info = info['entries'[0]]
                url = info['url']
                title = info['title']
                self.queue.append((url, title))
                await ctx.send(f'**{title}** ajoutée a la file')
        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)
    
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

client = commands.Bot(command_prefix='+', intents=intents)

async def main():
    await client.add_cog(MusicBot(client))
    await client.start(TOKEN)

asyncio.run(main())

