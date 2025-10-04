class Config:
    """Bot configuration settings"""

    # Bot Settings
    PREFIX = '!'

    # Embed Colors
    COLOR_SUCCESS = 0x00ff00
    COLOR_ERROR = 0xff0000
    COLOR_INFO = 0x3498db
    COLOR_WARNING = 0xffa500

    # Server Setup Defaults
    DEFAULT_CHANNELS = [
        {'name': 'welcome', 'type': 'text', 'category': 'Info'},
        {'name': 'rules', 'type': 'text', 'category': 'Info'},
        {'name': 'announcements', 'type': 'text', 'category': 'Info'},
        {'name': 'general', 'type': 'text', 'category': 'General'},
        {'name': 'bot-commands', 'type': 'text', 'category': 'General'},
        {'name': 'General Voice', 'type': 'voice', 'category': 'Voice Channels'},
    ]

    DEFAULT_ROLES = [
        {'name': 'Admin', 'color': 0xe74c3c, 'permissions': ['administrator']},
        {'name': 'Moderator', 'color': 0x3498db, 'permissions': ['manage_messages', 'kick_members', 'ban_members']},
        {'name': 'Member', 'color': 0x95a5a6, 'permissions': []},
    ]

    # Permission mappings
    PERMISSION_MAP = {
        'administrator': discord.Permissions.administrator,
        'manage_messages': discord.Permissions.manage_messages,
        'kick_members': discord.Permissions.kick_members,
        'ban_members': discord.Permissions.ban_members,
        'manage_channels': discord.Permissions.manage_channels,
        'manage_roles': discord.Permissions.manage_roles,
        'manage_guild': discord.Permissions.manage_guild,
    }


import discord