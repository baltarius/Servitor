# punishment.py
"""
Punishment system cog.

This cog is to allow a community to collectively punish
a member of a server with the command /punish [member].
This will put that member in timeout if the requirements
are met.

Author: Elcoyote Solitaire
"""
import asyncio
import discord

from datetime import timedelta
from discord import app_commands, Interaction
from discord.utils import get
from discord.ext import commands
from cogs.intercogs import get_server_database, get_time_zone, add_achievement



class Punishment(commands.Cog, name="punishment"):
    """
    Punishment class for the punishment's system.

    This class contains commands, automatic functions
    and listeners used for the punishment's system.

    Commands:
        /setpunishreq
        /setpunishtime
        /punish

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot


    async def punishreq(self, server_id):
        """
        Punishment requirement.

        This command is used to verify the requirement for
        the server for the punish function.

        see punish()
        
        Args:
            server_id as interaction.guild.id
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("punishreq",))
        punishreq = cur.fetchone()[0]
        if punishreq is not None:
            return punishreq

        punishreq = 10
        cur.execute("REPLACE INTO setup (chans, id) VALUES ('punishreq', '10')")
        conn.commit()
        conn.close()
        return punishreq


    async def start_timer(self, interaction, target_id: int, channel_id, message_id):
        """
        Timer for punishment.

        Using asyncio.sleep(300) to give 5 minutes to
        the users to type the command for a target.

        see punish()
        
        Args:
            interaction as discord.Interaction
            target_id as discord.Member.id (forced integer)
        """
        await interaction.response.send_message(
            f"Timer started for {interaction.guild.get_member(target_id)}.",
            ephemeral=True
        )
        await asyncio.sleep(300)  # 5 minutes
        await self.notify(interaction, target_id, channel_id, message_id)


    async def notify(self, interaction, target_id, channel_id, message_id):
        """
        Notification for punishment.

        Sends a message with a reply when the timer 
        is up for a target of the punish function.

        see start_timer()
        
        Args:
            interaction as discord.Interaction
            target_id as discord.Member.id (forced integer)
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT target FROM punishment WHERE target = ?", (target_id,))
        the_target = cur.fetchall()
        conn.close()
        if the_target:
            context = await self.bot.get_context(interaction)
            message = await context.fetch_message(message_id)
            embed = message.embeds[0]
            embed.add_field(
                name="Time's up!",
                value=f"Not enough people used the command against "
                    f"{interaction.guild.get_member(target_id).display_name}.",
                inline=False
            )
            await message.edit(embed=embed)
            await self.stop_timer(interaction, target_id)


    async def stop_timer(self, interaction, target_id: int):
        """
        Timer for punishment.

        Stops the timer for a target and after a successful
        use of the punish function on a target.

        see punish()
        
        Args:
            interaction as discord.Interaction
            target_id as discord.Member.id (forced integer)
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT target FROM punishment WHERE target = ?", (target_id,))
        the_target = cur.fetchall()
        if the_target:
            cur.execute("DELETE FROM punishment WHERE target = ?", (target_id,))
            conn.commit()
        conn.close()


    @app_commands.command(
        name="punish",
        description="Community's punishment to a member"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(3, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(target="Member to be punished")
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def punish(
        self, interaction: Interaction, target: discord.User
    ):
        """
        Punishment from the community.

        This command is used to punish a member of the
        server without the help of the moderation's team.

        Example:
            /punish @member

        Args:
            interaction as discord.Interaction.
            target as the @member to punish
        """
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not permissions.embed_links:
            await interaction.response.send_message(
                content="I don't have the permissions to send embed messages in "
                    f"{interaction.channel.mention}",
                ephemeral=True
            )
            return
        if target.bot:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content="Please don't punish our bots",
                ephemeral=True
            )
            return
        if target == interaction.user:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content="You can not punish yourself",
                ephemeral=True
            )
            return
        if target.is_timed_out() is True:
            time_zone = await get_time_zone(interaction.guild.id)
            formatted_time = target.timed_out_until.astimezone(
                time_zone).strftime("%m/%d - %H:%M")
            await interaction.response.send_message(
                content=f"{target} is already in timeout until {formatted_time} .",
                ephemeral=True
            )
            return
        if target not in interaction.guild.members:
            await interaction.response.send_message(
                content=f"{target} is not a member of {interaction.guild.name}.",
                ephemeral=True
            )
            return

        server_id = interaction.guild.id
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT starters FROM punishment WHERE target = ?", (target.id,))
        starters = cur.fetchall()
        punishreq = await self.punishreq(server_id)
        embed = discord.Embed(
            color=0x000000,
            title="Punishment",
            description=f"Target: {target.display_name}"
        )
        if starters:
            cur.execute(
                "SELECT message FROM punishment WHERE target = ? AND message IS NOT NULL",
                (target.id,)
            )
            message = cur.fetchone()[0]
            context = await self.bot.get_context(interaction)
            emb_resp = await context.fetch_message(message)
            embed = emb_resp.embeds[0]
            if str(interaction.user.id) in str(starters):
                await interaction.response.send_message(
                    f"You already used that command on {target.display_name}. "
                    f"{target.display_name} is now at {len(set(starters))}/{punishreq}",
                    ephemeral=True
                )
                conn.close()
                return

            cur.execute(
                "INSERT INTO punishment (target, starters) VALUES (?, ?)",
                (target.id, interaction.user.id,)
            )
            conn.commit()

            cur.execute("SELECT starters FROM punishment WHERE target = ?", (target.id,))
            starters = cur.fetchall()
            await interaction.response.send_message(
                content=f"{target.display_name} is now at {len(set(starters))}/{punishreq}",
                ephemeral=True
            )

            if len(set(starters)) == punishreq:
                cur.execute("SELECT id FROM setup WHERE chans = ?", ("punishtime",))
                punishtime = cur.fetchone()[0]
                conn.close()
                await target.timeout(timedelta(
                    minutes=punishtime),
                    reason="Timeout from the community"
                )
                authors = embed.fields[1].value
                authors += f"\n{interaction.user.display_name}"
                embed.set_field_at(1, name="list", value=authors)
                embed.add_field(
                    name="TIMEOUT!",
                    value=f"Community united! {target.mention} is now in timeout for "
                    f"{punishtime} minutes",
                    inline=False
                )
                embed.set_footer(
                    text=f"{len(set(starters))}/{punishreq}"
                )
                await emb_resp.edit(embed=embed)
                await self.stop_timer(interaction, target.id)
            else:
                authors = embed.fields[1].value
                authors += f"\n{interaction.user.display_name}"
                embed.set_field_at(1, name="list", value=authors)
                embed.set_footer(
                    text=f"{len(set(starters))}/{punishreq}"
                )
                await emb_resp.edit(embed=embed)
                conn.close()

        else:
            embed.add_field(
                name="Timer started by",
                value=interaction.user.display_name,
                inline=False
            )
            embed.add_field(
                name="list",
                value=interaction.user.display_name,
            )
            embed.set_footer(text=f"1/{punishreq}")
            message = await interaction.channel.send(embed=embed)
            cur.execute(
                "INSERT INTO punishment (target, starters, message, channel) VALUES (?, ?, ?, ?)",
                (target.id, interaction.user.id, message.id, interaction.channel.id)
            )
            conn.commit()
            conn.close()
            await self.start_timer(interaction, target.id, interaction.channel.id, message.id)


    @punish.error
    async def punish_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                content="You don't have the permissions to use that command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                content="I don't have the permissions to moderate members.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.CommandOnCooldown):
            await add_achievement(interaction.guild.id, interaction.user.id, "Cooldown!")
            await interaction.response.send_message(
                content=error,
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"Member not found. Please make sure you're mentioning it correctly.\n{error}",
            ephemeral=True
        )


    @app_commands.command(
        name="setpunishreq",
        description="Setup requirement for punishment"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(requirement="Amount of members casting the command to work (3~50)")

    async def setpunishreq(self, interaction: Interaction, requirement: int):
        """
        Requirement for punishment.

        This command allows admins to setup the minimum
        amount of users with /punish to punish a member.

        Example:
            /setpunishreq 10

        Args:
            interaction as discord.Interaction.
            requirement as an integer between 3 and 50.
        """
        if 3 <= requirement <= 50:
            conn, cur = get_server_database(interaction.guild.id)
            cur.execute(
                "INSERT OR REPLACE INTO setup (chans, id) VALUES ('punishreq', ?)", (requirement,)
            )
            conn.commit()
            await interaction.response.send_message(
                f"New requirement for punishment is {requirement}.",
                ephemeral=True
            )
            conn.close()
        else:
            await interaction.response.send_message(
                content="Requirement for punishment must be between 3 and 50",
                ephemeral=True
            )


    @setpunishreq.error
    async def setpunishreq_error(self, interaction, error):
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


    @app_commands.command(
        name="setpunishtime",
        description="Setup punishment length"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(length="Length of the timeout in minutes")

    async def setpunishtime(self, interaction: Interaction, length: int):
        """
        Length for a punishment.

        This command allows admins to setup 
        the length of a punishment.

        Example:
            /setpunishtime 60

        Args:
            interaction as discord.Interaction.
            Length in minutes as an integer.
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("INSERT OR REPLACE INTO setup (chans, id) VALUES ('punishtime', ?)", (length,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"New length for punishment is {length} minutes.",
            ephemeral=True
        )


    @setpunishtime.error
    async def setpunishtime_error(self, interaction, error):
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
    await bot.add_cog(Punishment(bot))
