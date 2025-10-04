import discord
from discord.ext import commands
import logging
from utils.config import Config

logger = logging.getLogger("discord_bot")


class VoiceCog(commands.Cog):
    """Cog for handling dynamic voice channels"""

    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # Track temporary voice channels

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes"""

        # User joined a voice channel
        if after.channel is not None:
            await self.handle_join(member, after.channel)

        # User left a voice channel
        if before.channel is not None:
            await self.handle_leave(before.channel)

    async def handle_join(self, member: discord.Member, channel: discord.VoiceChannel):
        """Handle user joining a voice channel"""

        # Check if they joined the "Join to Create" channel
        if channel.id == Config.VOICE_JOIN_CHANNEL_ID:
            try:
                # Get the category
                category = self.bot.get_channel(Config.VOICE_CATEGORY_ID)
                if not category:
                    logger.error(f"Category {Config.VOICE_CATEGORY_ID} not found")
                    return

                # Create a new voice channel
                new_channel = await category.create_voice_channel(
                    name=f"{member.display_name}'s Channel",
                    reason=f"Temporary voice channel for {member.name}"
                )

                # Set permissions for the creator
                await new_channel.set_permissions(
                    member,
                    manage_channels=True,
                    manage_permissions=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True,
                    priority_speaker=True
                )

                # Move the user to the new channel
                await member.move_to(new_channel)

                # Track this channel
                self.temp_channels[new_channel.id] = {
                    'channel': new_channel,
                    'creator': member.id
                }

                logger.info(f"Created temporary voice channel '{new_channel.name}' for {member.name}")

            except discord.Forbidden:
                logger.error("Bot lacks permissions to create voice channels")
            except discord.HTTPException as e:
                logger.error(f"Failed to create voice channel: {e}")
            except Exception as e:
                logger.error(f"Unexpected error creating voice channel: {e}")

    async def handle_leave(self, channel: discord.VoiceChannel):
        """Handle user leaving a voice channel"""

        # Check if this is a temporary channel
        if channel.id in self.temp_channels:
            # If the channel is empty, delete it
            if len(channel.members) == 0:
                try:
                    channel_name = channel.name
                    await channel.delete(reason="Temporary voice channel is empty")
                    del self.temp_channels[channel.id]
                    logger.info(f"Deleted empty temporary voice channel '{channel_name}'")

                except discord.Forbidden:
                    logger.error(f"Bot lacks permissions to delete channel {channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to delete channel: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error deleting channel: {e}")


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(VoiceCog(bot))