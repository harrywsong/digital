import discord
from discord.ext import commands
import asyncio
import logging
from utils.config import Config
from utils.logger import setup_logger, add_discord_handler

# Setup logger
logger = setup_logger()


class DiscordBot(commands.Bot):
    """Custom Discord Bot class"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=Config.COMMAND_PREFIX,
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        logger.info("Setting up bot...")

        # Load cogs
        try:
            await self.load_extension('cogs.voice')
            logger.info("Loaded voice cog")
        except Exception as e:
            logger.error(f"Failed to load voice cog: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'Bot is ready! Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')

        # Setup Discord log handler
        try:
            await add_discord_handler(logger, self, Config.LOG_CHANNEL_ID)
            logger.info("Discord log handler initialized")
        except Exception as e:
            logger.error(f"Failed to setup Discord log handler: {e}")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="voice channels"
            )
        )

    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        else:
            logger.error(f"Command error in {ctx.command}: {error}")
            await ctx.send("❌ An error occurred while executing the command.")


async def main():
    """Main function to run the bot"""

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Create and run bot
    bot = DiscordBot()

    try:
        async with bot:
            await bot.start(Config.TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid bot token provided")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")