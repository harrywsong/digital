import logging
import sys
from datetime import datetime
from pathlib import Path
import discord
import asyncio


class BotLogger:
    """Centralized logging for the Discord bot"""

    def __init__(self, name='DiscordBot', level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.discord_channels = {}  # {guild_id: channel_id}
        self.bot = None
        self.message_queue = []
        self.batch_task = None

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # File handler - logs to file
        file_handler = logging.FileHandler(
            log_dir / f'bot_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        # Console handler - logs to terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '[{asctime}] [{levelname}] {name}: {message}',
            style='{',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def set_bot(self, bot):
        """Set the bot instance for Discord logging"""
        self.bot = bot
        if not self.batch_task and self.bot:
            self.batch_task = asyncio.create_task(self._batch_send_logs())

    def set_discord_channel(self, guild_id, channel_id):
        """Set the Discord channel for logging in a specific guild"""
        self.discord_channels[guild_id] = channel_id

    def remove_discord_channel(self, guild_id):
        """Remove Discord logging for a guild"""
        if guild_id in self.discord_channels:
            del self.discord_channels[guild_id]

    async def _batch_send_logs(self):
        """Batch send logs to Discord every 5 seconds"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                await asyncio.sleep(5)

                if not self.message_queue:
                    continue

                # Group messages by guild
                guild_messages = {}
                for guild_id, message in self.message_queue:
                    if guild_id not in guild_messages:
                        guild_messages[guild_id] = []
                    guild_messages[guild_id].append(message)

                # Send batched messages
                for guild_id, messages in guild_messages.items():
                    if guild_id not in self.discord_channels:
                        continue

                    channel = self.bot.get_channel(self.discord_channels[guild_id])
                    if not channel:
                        continue

                    # Combine messages into codeblock (max 1990 chars to leave room for formatting)
                    batch = "\n".join(messages)
                    if len(batch) > 1990:
                        # Split if too long
                        chunks = [batch[i:i + 1990] for i in range(0, len(batch), 1990)]
                        for chunk in chunks:
                            await channel.send(f"```\n{chunk}\n```")
                    else:
                        await channel.send(f"```\n{batch}\n```")

                self.message_queue.clear()

            except Exception as e:
                print(f"Error sending Discord logs: {e}")

    def _log_to_discord(self, level, message):
        """Queue a log message for Discord"""
        if not self.bot or not self.discord_channels:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"

        # Add to queue for all configured guilds
        for guild_id in self.discord_channels.keys():
            self.message_queue.append((guild_id, formatted))

    def info(self, message):
        self.logger.info(message)
        self._log_to_discord("INFO", message)

    def debug(self, message):
        self.logger.debug(message)
        # Don't send DEBUG to Discord by default

    def warning(self, message):
        self.logger.warning(message)
        self._log_to_discord("WARN", message)

    def error(self, message):
        self.logger.error(message)
        self._log_to_discord("ERROR", message)

    def critical(self, message):
        self.logger.critical(message)
        self._log_to_discord("CRIT", message)


# Create global logger instance
logger = BotLogger()