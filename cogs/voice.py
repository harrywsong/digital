import discord
from discord import app_commands
from discord.ext import commands
from utils.config import Config
from utils.logger import logger


class VoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Store trigger channel IDs and their created channels
        self.trigger_channels = {}  # {guild_id: trigger_channel_id}
        self.created_channels = {}  # {channel_id: creator_id}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice channel joins and leaves"""

        # Handle joining a channel
        if after.channel:
            await self._handle_join(member, after.channel)

        # Handle leaving a channel
        if before.channel:
            await self._handle_leave(before.channel)

    async def _handle_join(self, member, channel):
        """Handle user joining a voice channel"""

        # Check if this is a trigger channel
        guild_id = channel.guild.id
        if guild_id not in self.trigger_channels:
            return

        if channel.id != self.trigger_channels[guild_id]:
            return

        logger.info(f"User {member.name} joined trigger channel in {channel.guild.name}")

        try:
            # Create new voice channel
            new_channel = await channel.category.create_voice_channel(
                name=f"{member.display_name}'s Channel",
                reason=f"Dynamic voice channel created for {member.name}"
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

            # Move user to new channel
            await member.move_to(new_channel)

            # Track this channel
            self.created_channels[new_channel.id] = member.id

            logger.info(f"Created dynamic channel '{new_channel.name}' (ID: {new_channel.id})")

        except discord.Forbidden:
            logger.error(f"Missing permissions to create voice channel in {channel.guild.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to create voice channel: {e}")

    async def _handle_leave(self, channel):
        """Handle user leaving a voice channel"""

        # Check if this is a bot-created channel
        if channel.id not in self.created_channels:
            return

        # If channel is empty, delete it
        if len(channel.members) == 0:
            try:
                logger.info(f"Deleting empty dynamic channel '{channel.name}' (ID: {channel.id})")
                await channel.delete(reason="Dynamic voice channel is empty")
                del self.created_channels[channel.id]
            except discord.Forbidden:
                logger.error(f"Missing permissions to delete channel {channel.name}")
            except discord.HTTPException as e:
                logger.error(f"Failed to delete channel: {e}")

    @app_commands.command(
        name="voice-setup",
        description="Set the trigger channel for creating dynamic voice channels"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_voice(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Set up dynamic voice channel system"""

        self.trigger_channels[interaction.guild.id] = channel.id

        embed = discord.Embed(
            title="✅ Voice Channel Setup Complete",
            description=f"Users joining {channel.mention} will automatically get their own voice channel!",
            color=Config.COLOR_SUCCESS
        )
        embed.add_field(
            name="Features",
            value="• Automatic channel creation\n• Creator gets admin permissions\n• Auto-delete when empty",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Voice trigger channel set to '{channel.name}' in {interaction.guild.name}")

    @app_commands.command(
        name="voice-disable",
        description="Disable the dynamic voice channel system"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_voice(self, interaction: discord.Interaction):
        """Disable dynamic voice channel system"""

        if interaction.guild.id in self.trigger_channels:
            del self.trigger_channels[interaction.guild.id]

            embed = discord.Embed(
                title="✅ Voice System Disabled",
                description="Dynamic voice channel system has been disabled.",
                color=Config.COLOR_WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Voice system disabled in {interaction.guild.name}")
        else:
            embed = discord.Embed(
                title="❌ Not Configured",
                description="The voice system is not currently configured.",
                color=Config.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="voice-info",
        description="Show current voice channel configuration"
    )
    async def voice_info(self, interaction: discord.Interaction):
        """Show voice channel system info"""

        if interaction.guild.id not in self.trigger_channels:
            embed = discord.Embed(
                title="ℹ️ Voice System Not Configured",
                description="An administrator needs to run `/voice-setup` first.",
                color=Config.COLOR_INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        trigger_channel_id = self.trigger_channels[interaction.guild.id]
        trigger_channel = interaction.guild.get_channel(trigger_channel_id)

        # Count active dynamic channels
        active_channels = sum(
            1 for ch_id in self.created_channels
            if interaction.guild.get_channel(ch_id) is not None
        )

        embed = discord.Embed(
            title="🎤 Voice Channel System",
            color=Config.COLOR_INFO
        )

        if trigger_channel:
            embed.add_field(
                name="Trigger Channel",
                value=trigger_channel.mention,
                inline=False
            )
        else:
            embed.add_field(
                name="Trigger Channel",
                value="⚠️ Channel not found (may have been deleted)",
                inline=False
            )

        embed.add_field(
            name="Active Dynamic Channels",
            value=str(active_channels),
            inline=True
        )

        embed.set_footer(text="Join the trigger channel to create your own voice channel!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))