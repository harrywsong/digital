import logging
import discord
from datetime import datetime
from typing import Optional


class DiscordLogHandler(logging.Handler):
    """Custom logging handler that sends logs to a Discord channel"""

    def __init__(self, bot, channel_id: int):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.channel: Optional[discord.TextChannel] = None

    async def setup(self):
        """Setup the channel reference"""
        try:
            self.channel = await self.bot.fetch_channel(self.channel_id)
        except Exception as e:
            print(f"Failed to setup log channel: {e}")

    def emit(self, record):
        """Send log record to Discord channel"""
        if self.channel is None:
            return

        try:
            log_entry = self.format(record)

            # Create embed based on log level
            if record.levelno >= logging.ERROR:
                color = discord.Color.red()
                emoji = "🔴"
            elif record.levelno >= logging.WARNING:
                color = discord.Color.orange()
                emoji = "🟠"
            elif record.levelno >= logging.INFO:
                color = discord.Color.blue()
                emoji = "🔵"
            else:
                color = discord.Color.light_grey()
                emoji = "⚪"

            embed = discord.Embed(
                title=f"{emoji} {record.levelname}",
                description=f"```{log_entry}```",
                color=color,
                timestamp=datetime.utcnow()
            )

            if record.pathname:
                embed.add_field(name="File", value=record.pathname, inline=False)

            # Schedule the coroutine to send the message
            import asyncio
            asyncio.create_task(self.channel.send(embed=embed))

        except Exception as e:
            print(f"Error sending log to Discord: {e}")


def setup_logger(name: str = "discord_bot") -> logging.Logger:
    """Setup and configure logger with console handler only"""

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    return logger


async def add_discord_handler(logger: logging.Logger, bot, channel_id: int):
    """Add Discord handler to logger after bot is ready"""
    discord_handler = DiscordLogHandler(bot, channel_id)
    await discord_handler.setup()

    discord_format = logging.Formatter('%(message)s')
    discord_handler.setFormatter(discord_format)
    discord_handler.setLevel(logging.INFO)

    logger.addHandler(discord_handler)
    logger.discord_handler = discord_handler