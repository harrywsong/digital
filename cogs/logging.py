import discord
from discord import app_commands
from discord.ext import commands
from utils.config import Config
from utils.logger import logger


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="log-setup",
        description="Set a channel to receive bot logs"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_logging(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set up Discord logging channel"""

        # Check if bot can send messages in the channel
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages:
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description=f"I don't have permission to send messages in {channel.mention}",
                color=Config.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Set the logging channel
        logger.set_discord_channel(interaction.guild.id, channel.id)

        embed = discord.Embed(
            title="✅ Logging Channel Set",
            description=f"Bot logs will now be sent to {channel.mention}",
            color=Config.COLOR_SUCCESS
        )
        embed.add_field(
            name="What gets logged:",
            value="• Bot startup/shutdown\n• Command usage\n• Errors and warnings\n• Voice channel events\n• Server setup actions",
            inline=False
        )
        embed.set_footer(text="Logs are batched and sent every 5 seconds")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Send a test message to the log channel
        await channel.send("```\n✅ Logging system activated! Bot logs will appear here.\n```")
        logger.info(f"Logging channel set to #{channel.name} in {interaction.guild.name}")

    @app_commands.command(
        name="log-disable",
        description="Disable Discord logging for this server"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_logging(self, interaction: discord.Interaction):
        """Disable Discord logging"""

        if interaction.guild.id not in logger.discord_channels:
            embed = discord.Embed(
                title="❌ Not Configured",
                description="Discord logging is not currently enabled.",
                color=Config.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        logger.remove_discord_channel(interaction.guild.id)

        embed = discord.Embed(
            title="✅ Logging Disabled",
            description="Bot logs will no longer be sent to Discord.",
            color=Config.COLOR_WARNING
        )
        embed.set_footer(text="Logs will still be saved to the logs/ folder")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Discord logging disabled in {interaction.guild.name}")

    @app_commands.command(
        name="log-info",
        description="Show current logging configuration"
    )
    async def log_info(self, interaction: discord.Interaction):
        """Show logging configuration"""

        if interaction.guild.id not in logger.discord_channels:
            embed = discord.Embed(
                title="ℹ️ Logging Not Configured",
                description="Discord logging is not currently enabled.\n\nUse `/log-setup` to enable it.",
                color=Config.COLOR_INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        channel_id = logger.discord_channels[interaction.guild.id]
        channel = interaction.guild.get_channel(channel_id)

        embed = discord.Embed(
            title="📋 Logging Configuration",
            color=Config.COLOR_INFO
        )

        if channel:
            embed.add_field(
                name="Log Channel",
                value=channel.mention,
                inline=False
            )
        else:
            embed.add_field(
                name="Log Channel",
                value="⚠️ Channel not found (may have been deleted)",
                inline=False
            )

        embed.add_field(
            name="Log Levels Sent to Discord",
            value="• INFO\n• WARNING\n• ERROR\n• CRITICAL",
            inline=True
        )

        embed.add_field(
            name="Batch Interval",
            value="5 seconds",
            inline=True
        )

        embed.set_footer(text="All logs are also saved to the logs/ folder")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="log-test",
        description="Send a test log message"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def test_logging(self, interaction: discord.Interaction):
        """Send a test log message"""

        if interaction.guild.id not in logger.discord_channels:
            embed = discord.Embed(
                title="❌ Not Configured",
                description="Please set up a logging channel with `/log-setup` first.",
                color=Config.COLOR_ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        logger.info(f"Test log message from {interaction.user.name}")
        logger.warning("This is a test warning message")
        logger.error("This is a test error message")

        embed = discord.Embed(
            title="✅ Test Logs Sent",
            description="Check your logging channel in a few seconds!",
            color=Config.COLOR_SUCCESS
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Logging(bot))