# examples.py
"""
A bunch of examples using all
sort of features from discord.py

Author: Elcoyote Solitaire
"""
import discord # usually needed

# allows easy access for /commands, @app_commands and discord.Interaction
from discord import app_commands, Interaction

# @commands for listeners and @tasks for tasks made in loop/intervals
from discord.ext import commands, tasks

# for prefix commands - DEPRECATED
from discord.ext.commands import Context

# Group and command are for groups of commands
# Choice for choices in /commands
# context_menu for commands with right click on members
# AppCommandContext and AppInstallationType are for user installed commands
from discord.app_commands import Choice, context_menu, command, Group, AppCommandContext, AppInstallationType




# Define a class for the cog, which should be the name of the file for easy loading.
# The class has to be capitalized, but the argument "name" should be in lower case.
# Add a solid docstring, so you don't have to go through the whole file when looking for something.
# Some info could be a short description, a longer description, functions, listeners, commands, etc.
# Note that the very bottom of the file should contain a function "setup" to allow the bot to load the class with the cog.
class Examples(commands.Cog, name="examples"):
    """
    Examples class to show how it works

    This class contains examples of possible
    features with the API wrapper discord.py

    Functions:
        my_function()

    Listeners:
        - on_message()
        - 

    Context_menu:
        info

    Commands:
        /talk

    Group:
        /admin
            - kick
    """
    # __init__ function to define self.bot coming from your main file.
    def __init__(self, bot):
        self.bot = bot
        # This line is for context_menu
        self.bot.tree.context_menu(name="info")(self.info_member)


    # Always use "async" function, and with at least the "self" argument.
    # This function can now be called in this cog using "await self.my_function()".
    async def my_function(self):
        """
        Example function that does absolutely nothing
        """
        pass



    # Opening a listener() with the decorator.
    # The listener is for "on_message", which requires message intents.
    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listening to messages for examples.

        See the link below to find the documentation about the Message class:
        https://discordpy.readthedocs.io/en/stable/api.html?highlight=on_message#discord.Message
        """
        the_text = message.content
        author = message.author
        channel = message.channel


    # Here's a few listeners available:
    # on_message_edit(before, after)
    # on_message_delete(message)
    # on_bulk_message_delete(messages)
    # on_raw_message_edit(payload)
    # on_raw_message_delete(payload)
    # on_raw_bulk_message_delete(payload)
    # on_poll_vote_add(user, answer)
    # on_poll_vote_remove(user, answer)
    # on_raw_poll_vote_add(payload)
    # on_raw_poll_vote_remove(payload)
    # on_reaction_add(reaction, user)
    # on_reaction_remove(reaction, user)
    # on_reaction_clear(message, reactions)
    # on_reaction_clear_emoji(reaction)
    # on_raw_reaction_add(payload)
    # on_raw_reaction_remove(payload)
    # on_raw_reaction_clear(payload)
    # on_raw_reaction_clear_emoji(payload)
    # on_voice_state_update(member, before, after)
    # on_member_join(self, member)
    # on_member_remove(self, member)
    # on_member_ban(self, guild, user)
    # on_member_update(self, before, after)
    #
    # NOTE: the difference between "normal" and "raw" is the availability of the content.
    # Using on_message_edit will only work if the message edited is in the bot's cache.
    # Using raw requires a payload, but a necessary extra step to ensure no event goes unchecked.
    # For privacy reasons, raw event don't show the previous states of the event,
    # like raw edit won't show the previous message before edition.



    # Function for the context_menu. Right click a member > apps > info_member.
    async def info_member(self, interaction: discord.Interaction, member: discord.Member):
        """
        Interaction menu function for member's info.

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        user_account_name = member.name
        user_id = member.id
        message_content = (
            f"This is the information for {member.mention}\n"
            f"User: {user_account_name}\nUser id: {user_id}"
        )
        await interaction.response.send_message(content=message_content, ephemeral=True)



    # Declaring a new /command with decorators
    @app_commands.command(
        name="talk",
        description="Sends a message to a specific channel"
    )
    # guild_only() allows to set this command to be available only in servers (not in DMs).
    @app_commands.guild_only()
    # has_permissions allows to choose the minimal permissions for the member to use it.
    # Link to all permissions: https://discordpy.readthedocs.io/en/stable/api.html#discord.Permissions
    @app_commands.checks.has_permissions(administrator=True)
    # Cooldown for the use of the command. In this example, the command can be used twice every 600 seconds.
    # Note that cooldowns are reset upon reloading the cog.
    @app_commands.checks.cooldown(2, 600.0, key=lambda i: (i.guild_id, i.user.id))
    # Description for the arguments of the command. Those description appear in discord when typing the command.
    @app_commands.describe(
        channel="Choose the channel where to speak",
        speech="What do you want the bot to say?"
    )
    async def talk(
        self, interaction: Interaction, channel: discord.TextChannel, *, speech: str
    ):
        """
        Send a message to a specific channel

        This command is used to make the bot send a
        message to a specific channel of the server.
        The command automatically adds "Beep." at the
        and begining and ". Boop." at the end of the 
        speech, for robot talk.

        Example:
            /talk #channel Hello world!

        Args:
            interaction as discord.Interaction.
            channel as discord.TextChannel Channel where to send the message.
            speech as str for the message to send.

        Note:
            Use discord.abc.GuildChannel instead of discord.TextChannel to include ALL textable channels
        """
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages:
            await interaction.response.send_message(
                content=f"I don't have the permissions to send messages in {channel.mention}",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Sending your message in #{channel}",
            ephemeral=True
        )
        await channel.send(content=speech)


    # If you don't have a global handler for errors, here's how to proceed.
    # For the list of all the exceptions:
    # https://discordpy.readthedocs.io/en/stable/api.html#discord.DiscordException
    @talk.error
    async def talk_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.MissingRole):
            await interaction.response.send_message(
                "You do not have the required role to use this command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                "I don't have the permissions to perform that command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the required permissions to run this command!",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )




    # Declaring a new group of commands.
    # See the link below for the documentation:
    # https://discordpy.readthedocs.io/en/stable/interactions/api.html?highlight=app_commands%20group#discord.app_commands.Group
    anniv_group = Group(
        name="admin",
        description="Group of command for admin",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True)
    )

    # Decorators to associate the next command to the admin's group.
    # It is important to use the docstring wisely with group command, for discord
    # uses the first line to display the information when typing the command.
    # In this case, typing /admin kick_member will show the description 
    # "Allows an admin to kick a member".
    @admin_group.command()
    @app_commands.describe(
        member="Member to be kicked",
        reason="Reason for the kick (optional)"
    )
    async def kick_member(
        self, interaction: Interaction, member: discord.Member, reason: str = None
    ):
        """
        Allows an admin to kick a member

        Usage:
            /admin kick_member @member

        Args:
            interaction as discord.Interaction
            member as discord.Member for the member to kick
        """
        await interaction.guild.kick(member, reason=reason)
        await interaction.response.send_message(
            content=f"{member.mention} has been kicked like you wanted!",
            ephemeral=True
        )



# Always end the file with a setup(bot) function to add the class to the bot when loading the cog
async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Examples(bot))
