import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import deque
import re
from typing import Optional
from utils.config import Config

logger = logging.getLogger("discord_bot")


class Song:
    """Represents a song in the queue"""

    def __init__(self, title: str, url: str, duration: int, thumbnail: str, requester: discord.Member):
        self.title = title
        self.url = url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

    def format_duration(self) -> str:
        """Format duration in seconds to MM:SS"""
        if self.duration == 0:
            return "Unknown"
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"


class MusicControlView(discord.ui.View):
    """Persistent view with music control buttons"""

    def __init__(self, music_cog):
        super().__init__(timeout=None)
        self.music_cog = music_cog

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary, custom_id="music_pause")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if player.voice_client and player.is_playing():
            player.voice_client.pause()
            await interaction.response.send_message("⏸️ Paused!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.secondary, custom_id="music_resume")
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if player.voice_client and player.voice_client.is_paused():
            player.voice_client.resume()
            await interaction.response.send_message("▶️ Resumed!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is paused!", ephemeral=True)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.primary, custom_id="music_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if not player.voice_client or not player.is_playing():
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
            return

        player.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped!", ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if player.voice_client:
            player.queue.clear()
            player.current = None
            player.voice_client.stop()
            await player.voice_client.disconnect()
            player.voice_client = None
            await interaction.response.send_message("⏹️ Stopped and disconnected!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Not connected to voice!", ephemeral=True)

    @discord.ui.button(label="📜 Queue", style=discord.ButtonStyle.secondary, custom_id="music_queue")
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if not player.queue and not player.current:
            await interaction.response.send_message("📭 Queue is empty!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎵 Music Queue",
            color=discord.Color.blue()
        )

        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"**[{player.current.title}]({player.current.url})**\n{player.current.format_duration()}",
                inline=False
            )

        if player.queue:
            queue_text = ""
            for i, song in enumerate(list(player.queue)[:10], 1):
                queue_text += f"{i}. **{song.title}** - {song.format_duration()}\n"

            if len(player.queue) > 10:
                queue_text += f"\n... and {len(player.queue) - 10} more"

            embed.add_field(name="Up Next", value=queue_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, custom_id="music_loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)
        player.loop = not player.loop

        status = "enabled ✅" if player.loop else "disabled ❌"
        await interaction.response.send_message(f"🔁 Loop {status}", ephemeral=True)

    @discord.ui.button(label="🎵 Now Playing", style=discord.ButtonStyle.secondary, custom_id="music_nowplaying")
    async def nowplaying_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = self.music_cog.get_player(interaction.guild.id)

        if not player.current:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{player.current.title}]({player.current.url})**",
            color=discord.Color.green()
        )
        embed.add_field(name="Duration", value=player.current.format_duration())
        embed.add_field(name="Requested by", value=player.current.requester.mention)
        embed.add_field(name="Loop", value="✅ Enabled" if player.loop else "❌ Disabled")
        if player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class VolumeModal(discord.ui.Modal, title='Set Volume'):
    volume_input = discord.ui.TextInput(
        label='Volume (0-100)',
        placeholder='Enter a number between 0 and 100',
        required=True,
        max_length=3
    )

    def __init__(self, music_cog):
        super().__init__()
        self.music_cog = music_cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            volume = int(self.volume_input.value)
            if not 0 <= volume <= 100:
                await interaction.response.send_message("❌ Volume must be between 0 and 100!", ephemeral=True)
                return

            player = self.music_cog.get_player(interaction.guild.id)
            player.volume = volume / 100

            if player.voice_client and player.voice_client.source:
                player.voice_client.source.volume = player.volume

            await interaction.response.send_message(f"🔊 Volume set to {volume}%", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)


class MusicPlayer:
    """Music player for a guild"""

    def __init__(self, guild_id: int, bot):
        self.guild_id = guild_id
        self.bot = bot
        self.queue = deque()
        self.current = None
        self.voice_client: Optional[discord.VoiceClient] = None
        self.loop = False
        self.volume = 0.5
        self.text_channel = None

    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        return self.voice_client and self.voice_client.is_playing()

    async def play_next(self):
        """Play the next song in queue"""
        if len(self.queue) > 0:
            self.current = self.queue.popleft()

            try:
                source = await self.create_source(self.current.url)
                self.voice_client.play(
                    source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.after_play(e), self.bot.loop
                    )
                )

                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**[{self.current.title}]({self.current.url})**",
                    color=discord.Color.green()
                )
                embed.add_field(name="Duration", value=self.current.format_duration())
                embed.add_field(name="Requested by", value=self.current.requester.mention)
                if self.current.thumbnail:
                    embed.set_thumbnail(url=self.current.thumbnail)

                if self.text_channel:
                    await self.text_channel.send(embed=embed)

            except Exception as e:
                logger.error(f"Error playing song: {e}")
                if self.text_channel:
                    await self.text_channel.send(f"❌ Error playing song: {str(e)}")
                await self.play_next()
        else:
            self.current = None

    async def after_play(self, error):
        """Called after a song finishes playing"""
        if error:
            logger.error(f"Player error: {error}")

        if self.loop and self.current:
            self.queue.appendleft(self.current)

        await self.play_next()

    async def create_source(self, url: str):
        """Create audio source from URL"""
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': False,
        }

        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            info = ytdl.extract_info(url, download=False)
            url2 = info['url']

        ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        source = discord.FFmpegPCMAudio(url2, **ffmpeg_opts)
        return discord.PCMVolumeTransformer(source, volume=self.volume)


class MusicCog(commands.Cog):
    """Music cog with YouTube and Spotify support"""

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.spotify = None
        self.control_panel_message = None

        # Initialize Spotify client if credentials are provided
        if Config.SPOTIFY_CLIENT_ID and Config.SPOTIFY_CLIENT_SECRET:
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=Config.SPOTIFY_CLIENT_ID,
                    client_secret=Config.SPOTIFY_CLIENT_SECRET
                )
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                logger.info("Spotify client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Spotify: {e}")

    async def cog_load(self):
        """Called when cog is loaded"""
        # Add persistent view
        self.bot.add_view(MusicControlView(self))

        # Setup control panel if music channel is configured
        if Config.MUSIC_CHANNEL_ID:
            await self.setup_control_panel()

    async def setup_control_panel(self):
        """Setup the music control panel in the dedicated channel"""
        try:
            channel = self.bot.get_channel(Config.MUSIC_CHANNEL_ID)
            if not channel:
                logger.warning(f"Music channel {Config.MUSIC_CHANNEL_ID} not found")
                return

            # Check for existing control panel
            async for message in channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    if message.embeds[0].title == "🎵 Music Control Panel":
                        self.control_panel_message = message
                        return

            # Create new control panel
            embed = discord.Embed(
                title="🎵 Music Control Panel",
                description="Use `/play <song>` to add songs to the queue!\n\nUse the buttons below to control playback:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Commands",
                value="⏸️ **Pause** - Pause the current song\n"
                      "▶️ **Resume** - Resume playback\n"
                      "⏭️ **Skip** - Skip to next song\n"
                      "⏹️ **Stop** - Stop and disconnect\n"
                      "📜 **Queue** - View the queue\n"
                      "🔁 **Loop** - Toggle loop mode\n"
                      "🎵 **Now Playing** - Show current song",
                inline=False
            )
            embed.set_footer(text="Music bot is ready!")

            view = MusicControlView(self)
            self.control_panel_message = await channel.send(embed=embed, view=view)
            logger.info("Music control panel created")

        except Exception as e:
            logger.error(f"Failed to setup control panel: {e}")

    def get_player(self, guild_id: int) -> MusicPlayer:
        """Get or create music player for guild"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id, self.bot)
        return self.players[guild_id]

    async def extract_info(self, query: str, requester: discord.Member):
        """Extract song info from URL or search query"""
        ytdl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'default_search': 'ytsearch',
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
                if not query.startswith('http'):
                    query = f"ytsearch:{query}"

                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False)
                )

                if 'entries' in info:
                    info = info['entries'][0]

                song = Song(
                    title=info.get('title', 'Unknown'),
                    url=info.get('webpage_url', info.get('url')),
                    duration=info.get('duration', 0),
                    thumbnail=info.get('thumbnail'),
                    requester=requester
                )
                return song

        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            raise

    async def process_spotify_url(self, url: str, requester: discord.Member):
        """Process Spotify URL and return list of songs"""
        if not self.spotify:
            raise ValueError(
                "Spotify integration not configured. Please add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to your .env file.")

        songs = []
        spotify_uri_match = re.search(r'spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)', url)

        if not spotify_uri_match:
            raise ValueError("Invalid Spotify URL")

        content_type = spotify_uri_match.group(1)
        content_id = spotify_uri_match.group(2)

        try:
            if content_type == 'track':
                track = self.spotify.track(content_id)
                query = f"{track['name']} {track['artists'][0]['name']}"
                song = await self.extract_info(query, requester)
                songs.append(song)

            elif content_type == 'playlist':
                playlist = self.spotify.playlist(content_id)
                total = len(playlist['tracks']['items'])
                for i, item in enumerate(playlist['tracks']['items'][:50], 1):
                    track = item['track']
                    if track:
                        query = f"{track['name']} {track['artists'][0]['name']}"
                        try:
                            song = await self.extract_info(query, requester)
                            songs.append(song)
                        except:
                            continue

            elif content_type == 'album':
                album = self.spotify.album(content_id)
                for track in album['tracks']['items'][:50]:
                    query = f"{track['name']} {track['artists'][0]['name']}"
                    try:
                        song = await self.extract_info(query, requester)
                        songs.append(song)
                    except:
                        continue

        except Exception as e:
            logger.error(f"Spotify error: {e}")
            raise

        return songs

    @app_commands.command(name='play', description='Play a song from YouTube or Spotify')
    @app_commands.describe(query='Song name, YouTube URL, or Spotify URL')
    async def play(self, interaction: discord.Interaction, query: str):
        """Play a song from YouTube or Spotify"""
        # Check if music channel is configured and enforce it
        if Config.MUSIC_CHANNEL_ID and interaction.channel.id != Config.MUSIC_CHANNEL_ID:
            music_channel = self.bot.get_channel(Config.MUSIC_CHANNEL_ID)
            await interaction.response.send_message(
                f"❌ Please use music commands in {music_channel.mention}!",
                ephemeral=True
            )
            return

        if not interaction.user.voice:
            await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
            return

        await interaction.response.defer()

        player = self.get_player(interaction.guild.id)
        player.text_channel = interaction.channel

        if not player.voice_client:
            player.voice_client = await interaction.user.voice.channel.connect()

        try:
            if 'spotify.com' in query:
                songs = await self.process_spotify_url(query, interaction.user)

                for song in songs:
                    player.queue.append(song)

                embed = discord.Embed(
                    title="✅ Added to Queue",
                    description=f"Added **{len(songs)}** songs from Spotify",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)

            else:
                song = await self.extract_info(query, interaction.user)
                player.queue.append(song)

                embed = discord.Embed(
                    title="✅ Added to Queue",
                    description=f"**[{song.title}]({song.url})**",
                    color=discord.Color.green()
                )
                embed.add_field(name="Duration", value=song.format_duration())
                embed.add_field(name="Position in Queue", value=str(len(player.queue)))
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                await interaction.followup.send(embed=embed)

            if not player.is_playing():
                await player.play_next()

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @app_commands.command(name='volume', description='Set volume (0-100)')
    @app_commands.describe(volume='Volume level from 0 to 100')
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set volume (0-100)"""
        player = self.get_player(interaction.guild.id)

        if not 0 <= volume <= 100:
            await interaction.response.send_message("❌ Volume must be between 0 and 100!", ephemeral=True)
            return

        player.volume = volume / 100

        if player.voice_client and player.voice_client.source:
            player.voice_client.source.volume = player.volume

        await interaction.response.send_message(f"🔊 Volume set to {volume}%", ephemeral=True)

    @app_commands.command(name='clear', description='Clear the entire queue')
    async def clear(self, interaction: discord.Interaction):
        """Clear the queue"""
        player = self.get_player(interaction.guild.id)

        if not player.queue:
            await interaction.response.send_message("❌ Queue is already empty!", ephemeral=True)
            return

        queue_size = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(f"🗑️ Cleared {queue_size} song(s) from the queue!", ephemeral=True)


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(MusicCog(bot))