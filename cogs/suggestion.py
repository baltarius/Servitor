# suggestion.py
"""
Suggestion system cog.

This cog is for the suggestion's system, which allows users to
create a suggestions that will be then displayed in another
specified channel where people will be able to vote with one
reaction per user, but also creates a thread so people can
discuss more about it and creator can add extra attachments.

The decision system allows the admin to approve/deny/considerate
any suggestion using the suggestion's ID number then removes all
the reaction votes from the embed message to include the stats 
in the embed itself, changes the color accordingly with the
decision and states the decision and who took it.

Note: the timestamp in the embed shows the time the suggestion
was made first, then update to when the decision was taken. To
know when the suggestion was made, refer to the embed message
time of creation in discord.

Author: Elcoyote Solitaire
"""
import asyncio
import pytz
import discord

from datetime import datetime
from discord import app_commands, Interaction
from discord.utils import get
from discord.ext import commands
from discord.app_commands import Choice
from cogs.intercogs import get_server_database, get_time_zone, add_achievement



class Suggestion(commands.Cog, name="suggestion"):
    """
    Suggestion class for the suggestion system.

    This class contains commands, automatic functions
    and listeners used for the suggestion's system.

    Commands:
        /suggest
        /decision

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="suggest",
        description="Create a suggestion."
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(2, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(suggestion="The suggestion you want to submit to be voted on.")
    async def suggest(self, interaction: Interaction, *, suggestion: str):
        """
        Function to create a suggestion.

        This function will create an embed text of your suggestion with
        the necessary informations to be voted in a dedicated channel.

        Args:
            interaction as discord.Interaction
            suggestion: The suggestion as a str
        """
        user = interaction.user
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("vote",))
        row = cur.fetchone()
        if not row:
            await interaction.response.send_message(
                content="There is no vote channel set. Please contact an admin.",
                ephemeral=True
            )
            return
        votechanname = self.bot.get_channel(row[0])
        permissions = votechanname.permissions_for(interaction.guild.me)
        if not (
            permissions.embed_links and permissions.add_reactions and
            permissions.create_public_threads and permissions.manage_threads and
            permissions.send_messages_in_threads
        ):
            await interaction.response.send_message(
                content=f"I don't have the required permissions in {votechanname.mention}. "
                    "Please contact an admin.",
                ephemeral=True
            )
            return

        time_zone = await get_time_zone(interaction.guild.id)
        cur.execute("SELECT MAX(number) FROM suggestion")
        result = cur.fetchone()
        number = result[0] + 1 if result[0] is not None else 1
        embed = discord.Embed(
            title=f"Suggestion #{number}",
            color=0x0000FF,
            description=suggestion
        )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar)
        embed.set_footer(
            text=f"Suggested by: {interaction.user.display_name}"
        )

        suggestion_msg = await votechanname.send(embed=embed)
        embed.timestamp = datetime.now(time_zone)
        await suggestion_msg.add_reaction("⬆️")
        await asyncio.sleep(1)
        await suggestion_msg.add_reaction("⬇️")
        cur.execute(
            "INSERT INTO suggestion (id, authorid) VALUES (?, ?)", (suggestion_msg.id, user.id,)
        )
        conn.commit()
        conn.close()
        sugg_thread = await suggestion_msg.create_thread(
            name=f"Suggestion #{number}",
            auto_archive_duration=4320,
            slowmode_delay=30,
            reason=f"Thread creation for suggestion #{number}"
        )
        await sugg_thread.send(
            content=f"{user.mention} Please use this thread to add any comment "
                "and/or file that concerns your suggestion."
        )
        await add_achievement(interaction.guild.id, user.id, "Suggestion")
        await interaction.response.send_message(
            content=f"Suggestion #{number} confirmed",
            ephemeral=True
        )


    @suggest.error
    async def suggest_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.CommandOnCooldown):
            await add_achievement(interaction.guild.id, interaction.user.id, "Cooldown!")
            await interaction.response.send_message(
                content=error,
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        Listener to reactions.

        This will make sure users don't react with
        both arrows (up and down) on a suggestion.

        Args:
            None
        """
        if payload.member.bot:
            return
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel_or_thread(payload.channel_id)
        if isinstance(channel, discord.Thread):
            return
        message = await channel.fetch_message(payload.message_id)
        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        user = guild.get_member(payload.user_id)
        conn, cur = get_server_database(guild.id)
        cur.execute("SELECT * FROM suggestion WHERE id = ?", (payload.message_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            await add_achievement(guild.id, user.id, "Vote")
            if reaction.emoji == "⬆️":
                down_reaction = discord.utils.get(message.reactions, emoji="⬇️")
                if down_reaction:
                    users = down_reaction.users()
                    async for member in users:
                        if member == user:
                            # The user has already reacted with ⬇️, so remove their reaction
                            await reaction.remove(user)
                            break
            elif reaction.emoji == "⬇️":
                up_reaction = discord.utils.get(message.reactions, emoji="⬆️")
                if up_reaction:
                    users = up_reaction.users()
                    async for member in users:
                        if member == user:
                            # The user has already reacted with ⬆️, so remove their reaction
                            await reaction.remove(user)
                            break


    @app_commands.command(
        name="decision",
        description="Take a decision on a suggestion"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        sugg_id="The ID of the suggestion for the decision",
        result="Choose either approve, deny or considerate",
        reason="Enter an optionnal reason for the decision"
    )
    @app_commands.choices(result=[
        Choice(name="approve", value=1),
        Choice(name="deny", value=2),
        Choice(name="considerate", value=3)
    ])
    async def decision(self, interaction: Interaction, sugg_id: int,
        result: Choice[int], reason: str = None):
        """
        Function to approve a suggestion.

        This will first make sure the /suggestion is used in the
        suggestion channel, then will copy the suggestion into
        the vote channel, adding a up and down reaction to allow
        people to vote, to finaly delete the suggestion from the
        suggestion channel.

        Args:
            interaction as discord.Interaction
            sugg_id: The suggestion's number as an integer
            result: a CHOICE between approve/deny/considerate
            reason: The reason why the suggestion is approve
                as a string. None by default
        """
        guild = interaction.guild
        conn, cur = get_server_database(guild.id)
        cur.execute("SELECT * FROM suggestion WHERE number = ?", (sugg_id,))
        suggtable = cur.fetchone()
        if suggtable and suggtable[3] is None:
            time_zone = await get_time_zone(guild.id)
            author_name = self.bot.get_user(suggtable[2])
            cur.execute("SELECT id FROM setup WHERE chans = ?", ("vote",))
            vote_id = cur.fetchone()[0]
            vote_name = interaction.guild.get_channel(vote_id)
            message = await vote_name.fetch_message(suggtable[1])
            embed = message.embeds[0]
            created_time = message.created_at.astimezone(time_zone)
            reactionup = discord.utils.get(message.reactions, emoji="⬆️")
            reactiondown = discord.utils.get(message.reactions, emoji="⬇️")
            countup = reactionup.count if reactionup else 0
            countdown = reactiondown.count if reactiondown else 0
            countup -= 1
            countdown -= 1
            embed.add_field(
                name="Votes",
                value=f"⬆️: {countup} \n️⬇️: {countdown}"
            )
            if result.name == "approve":
                embed.add_field(
                    name=" ",
                    value=f"Suggested by: {author_name.name}"
                    f"({created_time.strftime('%Y-%m-%d %H:%M:%S')}) \n"
                    f"***APPROVED*** \nReason: {reason}",
                    inline=False
                )
                embed.color=0x008000
                embed.timestamp = datetime.now(time_zone)
            elif result.name == "deny":
                embed.add_field(
                    name=" ",
                    value=f"Suggested by: {author_name.name}"
                        f"({created_time.strftime('%Y-%m-%d %H:%M:%S')}) \n"
                        f"***DENIED*** \nReason: {reason}",
                    inline=False
                )
                embed.color=0xFF0000
                embed.timestamp = datetime.now(time_zone)
            elif result.name == "considerate":
                embed.add_field(
                    name=" ",
                    value=f"Suggested by: {author_name.name}"
                        f"({created_time.strftime('%Y-%m-%d %H:%M:%S')}) \n"
                        f"***CONSIDERATED*** \nReason: {reason}",
                    inline=False
                )
                embed.color=0xFCAE1E
                embed.timestamp = datetime.now(time_zone)
            else:
                await interaction.response.send_message(
                    content=f"Invalid decision ({result}).",
                    ephemeral=True
                )

            embed.set_footer(text=f"Decision made by: {interaction.user.display_name}")
            await message.edit(embed=embed)
            the_file = message.attachments
            await message.remove_attachments(the_file)
            await message.clear_reactions()
            cur.execute(
                "UPDATE suggestion SET decision = ? WHERE number = ?", (result.name, sugg_id)
            )
            conn.commit()
            conn.close()
            await interaction.response.send_message(
                content=f"Embed message set as {result.name}.",
                ephemeral=True
            )
        else:
            conn.close()
            if not suggtable:
                await interaction.response.send_message(
                    content=f"Suggestion #{sugg_id} not found.",
                    ephemeral=True
                )
            else: 
                await interaction.response.send_message(
                    content=f"Suggestion #{sugg_id} has already been set as: {suggtable[3]}.",
                    ephemeral=True
                )



    @decision.error
    async def decision_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Suggestion(bot))
