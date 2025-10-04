import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for Discord bot"""

    # Bot Token
    TOKEN = os.getenv('DISCORD_TOKEN')

    # Logging Channel
    LOG_CHANNEL_ID = 1423884966588186714

    # Voice Channel Configuration
    VOICE_CATEGORY_ID = 1423888180712833125
    VOICE_JOIN_CHANNEL_ID = 1423888213105180712

    # Music Bot Channel
    MUSIC_CHANNEL_ID = 1423898796202659941

    # Spotify Configuration (Optional)
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

    # Bot Settings
    COMMAND_PREFIX = '!'

    @classmethod
    def validate(cls):
        """Validate that all required config values are set"""
        if not cls.TOKEN:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
        return True