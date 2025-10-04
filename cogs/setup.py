import discord
from discord import app_commands
from discord.ext import commands
from utils.config import Config


class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Set up your server with default channels and roles")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction):
        """Interactive server setup command"""

        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🚀 Server Setup",
            description="Would you like to set up this server with default channels and roles?",
            color=Config.COLOR_INFO
        )
        embed.add_field(
            name="What will be created:",
            value="• Info, General, and Voice categories\n• Welcome, Rules, Announcements channels\n• Admin, Moderator, and Member roles",
            inline=False
        )

        view = SetupConfirmView(self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="setup-channels", description="Create default channels only")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channels(self, interaction: discord.Interaction):
        """Create default channels"""

        await interaction.response.defer(ephemeral=True)

        try:
            created = await self.create_channels(interaction.guild)

            embed = discord.Embed(
                title="✅ Channels Created",
                description=f"Successfully created {created} channels!",
                color=Config.COLOR_SUCCESS
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to create channels: {str(e)}",
                color=Config.COLOR_ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setup-roles", description="Create default roles only")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        """Create default roles"""

        await interaction.response.defer(ephemeral=True)

        try:
            created = await self.create_roles(interaction.guild)

            embed = discord.Embed(
                title="✅ Roles Created",
                description=f"Successfully created {created} roles!",
                color=Config.COLOR_SUCCESS
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to create roles: {str(e)}",
                color=Config.COLOR_ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def create_channels(self, guild):
        """Create default channels and categories"""
        categories = {}
        created_count = 0

        for channel_data in Config.DEFAULT_CHANNELS:
            category_name = channel_data['category']

            # Create category if it doesn't exist
            if category_name not in categories:
                category = discord.utils.get(guild.categories, name=category_name)
                if not category:
                    category = await guild.create_category(category_name)
                categories[category_name] = category

            # Check if channel already exists
            existing = discord.utils.get(guild.channels, name=channel_data['name'])
            if existing:
                continue

            # Create channel
            if channel_data['type'] == 'text':
                await categories[category_name].create_text_channel(channel_data['name'])
            elif channel_data['type'] == 'voice':
                await categories[category_name].create_voice_channel(channel_data['name'])

            created_count += 1

        return created_count

    async def create_roles(self, guild):
        """Create default roles"""
        created_count = 0

        for role_data in Config.DEFAULT_ROLES:
            # Check if role already exists
            existing = discord.utils.get(guild.roles, name=role_data['name'])
            if existing:
                continue

            # Build permissions
            perms = discord.Permissions.none()
            for perm_name in role_data['permissions']:
                if perm_name in Config.PERMISSION_MAP:
                    setattr(perms, perm_name, True)

            # Create role
            await guild.create_role(
                name=role_data['name'],
                color=discord.Color(role_data['color']),
                permissions=perms
            )
            created_count += 1

        return created_count


class SetupConfirmView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.button(label="Confirm Setup", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        setup_cog = self.bot.get_cog('Setup')

        try:
            channels = await setup_cog.create_channels(interaction.guild)
            roles = await setup_cog.create_roles(interaction.guild)

            embed = discord.Embed(
                title="✅ Setup Complete!",
                description=f"Server setup completed successfully!",
                color=Config.COLOR_SUCCESS
            )
            embed.add_field(name="Channels Created", value=str(channels), inline=True)
            embed.add_field(name="Roles Created", value=str(roles), inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Setup Failed",
                description=f"An error occurred: {str(e)}",
                color=Config.COLOR_ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Setup Cancelled",
            description="Server setup has been cancelled.",
            color=Config.COLOR_WARNING
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


async def setup(bot):
    await bot.add_cog(Setup(bot))