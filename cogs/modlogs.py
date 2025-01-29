# modlogs.py
"""
Moderation logs system cog.

This cog is for logging different event to make
the moderation more efficient, easier and safer.

This system includes the listeners to log
everything in the moderation's channels.

Author: Elcoyote Solitaire
"""
import random
import datetime
import pytz
import discord
import emoji

from datetime import datetime
from discord.ext import commands
from cogs.intercogs import get_server_database, is_exception, get_time_zone, add_achievement



class Modlogs(commands.Cog, name="modlogs"):
    """
    Modlogs class for the logging system.

    This class contains automatic functions
    and listeners used for the modlogs' system.
    """
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """
        Listener to message edition.

        This will post an embed in a specific channel
        when any message is edited. The post will
        show the before and after the editing.

        The listener also takes in consideration when
        a channel is added to the exception's list.

        Args:
            None
        """
        if str(after.channel.type) == "private":
            return
        if after.author.bot:
            return
        if before.content == after.content:
            return

        conn, cur = get_server_database(after.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("edits",))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        editschanname = self.bot.get_channel(row[0])
        permissions = editschanname.permissions_for(editschanname.guild.me)
        if not permissions.embed_links:
            return
        time_zone = await get_time_zone(after.guild.id)
        created_timestamp = before.created_at.astimezone(time_zone).strftime("%Y-%m-%d %H:%M:%S")
        edited_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        embed = discord.Embed(
            color=0xF1C40F,
            url=after.jump_url,
            title="Message edited\n"
            f"in {after.channel.mention}",
            description=f"***Before***: {before.content}\n"
            f"***@After***: {after.content}"
        )
        embed.add_field(
            name="",
            value=f"\nBefore: (created at {created_timestamp}) \n"
                f"After: (edited at: {edited_timestamp})",
            inline=False
        )
        for attachment in before.attachments:
            embed.set_image(url=attachment.url)
            embed.add_field(name="Attachment", value=attachment.url, inline=False)
        for attachment in after.attachments:
            embed.set_image(url=attachment.url)
            embed.add_field(name="Attachment", value=attachment.url, inline=False)
        if after.author.avatar:
            embed.set_footer(
                text=f"Message from: {after.author.display_name}",
                icon_url=after.author.avatar.url
            )
        else:
            embed.set_footer(text=f"Message from: {after.author.display_name}")
        embed.timestamp = datetime.now(time_zone)
        await editschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """
        Listener to deletion.

        This will post an embed in a specific channel
        when any message is deleted. The post will
        show the message and the author.

        The listener also takes in consideration when
        a channel is added to the exception's list.

        Args:
            None
        """
        if str(message.channel.type) == "private":
            return
        if not message.guild:
            return
        conn, cur = get_server_database(message.guild.id)
        if not is_exception(message.guild.id, message.channel.id, "delete"):
            cur.execute("SELECT id FROM setup WHERE chans = ?", ("edits",))
            row = cur.fetchone()
            conn.close()
            if row:
                editschanname = self.bot.get_channel(row[0])
                permissions = editschanname.permissions_for(editschanname.guild.me)
                if not permissions.embed_links:
                    return
                time_zone = await get_time_zone(message.guild.id)
                time_created = (
                    message.created_at.astimezone(time_zone).strftime("%Y-%m-%d %H:%M:%S")
                )
                embed = discord.Embed(
                    color=0xFF0000,
                    title=f"Message deleted \nin: {message.channel.mention}",
                    description=f"***message***: {message.content}"
                )
                embed.add_field(
                    name="",
                    value=f"\nMessage: created at {time_created}", inline=False
                )
                if message.author.avatar:
                    embed.set_footer(
                        text=f"Message from: {message.author.display_name}",
                        icon_url=message.author.avatar.url
                    )
                else:
                    embed.set_footer(text=f"Message from: {message.author.display_name}")
                for attachment in message.attachments:
                    embed.set_image(url=attachment.url)
                    embed.add_field(name="Attachment", value=attachment.url, inline=False)
                embed.timestamp = datetime.now(time_zone)
                await editschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_bulk_message_delete(self, message):
        """
        Listener to deletion.

        This will post an embed in a specific channel
        when any message is deleted. The post will
        show the message and the author.

        The listener also takes in consideration when
        a channel is added to the exception's list.

        Args:
            None
        """
        guild = message[0].guild
        server_id = guild.id
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("edits",))
        row = cur.fetchone()
        conn.close()
        if not row:
            return
        async for entry in guild.audit_logs(action=discord.AuditLogAction.message_delete):
            if entry.target.id in [msg.author.id for msg in message]:
                responsible_user = entry.user
                embed = discord.Embed(color=0xF1C40F, title=f"Deleted by: {responsible_user}")
                editschan = int(row[0])
                editschanname = self.bot.get_channel(editschan)
                await editschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Listener to member joining the server.

        This will post an embed in a specific channel
        when someone join your server. The embed will
        include a few useful informations about the
        new member, like when the account was created
        and it's ID.

        The listener also sends a welcome message in
        a specific channel with a random message.

        Args:
            None
        """
        conn, cur = get_server_database(member.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("joins",))
        row = cur.fetchone()
        if row:
            joinschanname = self.bot.get_channel(row[0])
            permissions = joinschanname.permissions_for(joinschanname.guild.me)
            if not permissions.embed_links:
                return
            time_zone = await get_time_zone(member.guild.id)

            created_gap = datetime.now(pytz.utc) - member.created_at
            years = created_gap.days // 365
            months = (created_gap.days % 365) // 30
            weeks = ((created_gap.days % 365) % 30) // 7
            days = ((created_gap.days % 365) % 30) % 7
            hours = created_gap.seconds // 3600
            minutes = (created_gap.seconds // 60) % 60
            seconds = created_gap.seconds % 60
            time_components = [
                (years, "years"),
                (months, "months"),
                (weeks, "weeks"),
                (days, "days"),
                (hours, "hours"),
                (minutes, "minutes"),
                (seconds, "seconds"),
            ]
            time_strings = [f"{value}{label}" for value, label in time_components if value != 0]
            time_string = ", ".join(time_strings)

            embed = discord.Embed(color=0x00D100, title=member)
            embed.set_thumbnail(url=member.avatar)
            embed.add_field(
                name="Member joined",
                value=f"{member.display_name} ({member.id})\n"
                    "Created "
                    f"{member.created_at.astimezone(time_zone).strftime('%Y-%m-%d %H:%M:%S')}."
                    f"\nAccount created {time_string} ago."
            )
            if created_gap.days < 7:
                embed.add_field(
                    name="NEW ACCOUNT",
                    value=f"{emoji.emojize(':warning:')} ACCOUNT CREATED LESS THAN A WEEK AGO \n"
                        f"{emoji.emojize(':warning:')}",
                    inline=False
                )
            await joinschanname.send(embed=embed)

            welcome_msgs = [
                f"Welcome aboard **{member.display_name}**!",
                f"It is a pleasure to have you here **{member.display_name}**!",
                f"Oy! **{member.display_name}** just arrived!"
            ]
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("welcome",))
        row = cur.fetchone()
        conn.close()
        if row:
            welcomechanname = self.bot.get_channel(row[0])
            await welcomechanname.send(random.choice(welcome_msgs))


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """
        Listener member leaving the server.

        This will post an embed in a specific channel
        when any member leaves the server. The post
        will show informations about the user, such as
        for how long he was on the server.

        Args:
            None
        """
        conn, cur = get_server_database(member.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("lefts",))
        row = cur.fetchone()
        conn.close()
        if row:
            leftschanname = self.bot.get_channel(row[0])
            permissions = leftschanname.permissions_for(leftschanname.guild.me)
            if not permissions.embed_links:
                return
            time_zone = await get_time_zone(member.guild.id)

            joined_gap = datetime.now(pytz.utc) - member.joined_at
            years = joined_gap.days // 365
            months = (joined_gap.days % 365) // 30
            weeks = ((joined_gap.days % 365) % 30) // 7
            days = ((joined_gap.days % 365) % 30) % 7
            hours = joined_gap.seconds // 3600
            minutes = (joined_gap.seconds // 60) % 60
            seconds = joined_gap.seconds % 60
            time_components = [
                (years, "years"),
                (months, "months"),
                (weeks, "weeks"),
                (days, "days"),
                (hours, "hours"),
                (minutes, "minutes"),
                (seconds, "seconds"),
            ]
            time_strings = [f"{value}{label}" for value, label in time_components if value != 0]
            time_string = ", ".join(time_strings)

            role_names = [role.name for role in member.roles if role.name != "@everyone"]
            user_roles = ', '.join(role_names) if role_names else "None"

            embed = discord.Embed(color=0xFF0000, title=member)
            embed.set_thumbnail(url=member.avatar)
            embed.add_field(
                name="Member left",
                value=f"{member.display_name} ({member.id}) \nJoined"
                    f"{member.joined_at.astimezone(time_zone).strftime('%Y-%m-%d %H:%M:%S')} \n"
                    f"member left after {time_string}.\n Roles: {user_roles}"
            )

            await leftschanname.send(embed=embed)

            guild = member.guild
            if guild.me.guild_permissions.view_audit_log:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                    if entry.target == member:
                        moderator = entry.user
                        reason = entry.reason
                        if reason is None:
                            reason = "No reason provided"

                        embedkick = discord.Embed(color=0xFF0000, title=member)
                        embedkick.set_thumbnail(url=member.avatar)
                        embedkick.add_field(
                            name="Member kicked",
                            value=f"{member.display_name} ({member.id}) \nKicked by {moderator}\n"
                            f"Reason: {reason}"
                        )
                        await leftschanname.send(embed=embedkick)



    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """
        Listener member banned from server.

        This will post an embed in a specific channel
        when a member receives a ban from the guild.
        

        Args:
            None
        """
        conn, cur = get_server_database(guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("lefts",))
        row = cur.fetchone()
        conn.close()
        if row:
            if guild.me.guild_permissions.view_audit_log:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                    if entry.target == user:
                        moderator = entry.user
                    else:
                        moderator = "No name in audit"
            else:
                moderator = "no view audit"

            if guild.me.guild_permissions.ban_members:
                the_ban = await guild.fetch_ban(user)
                reason = the_ban.reason
            else:
                reason = "Can't access reason"

            embed = discord.Embed(color=0xFF0000, title=user)
            embed.set_thumbnail(url=user.avatar)
            embed.add_field(
                name=f"MEMBER {user.mention} BANNED",
                value=f"Moderator: {moderator}\nReason: {reason}."
            )
            chan_left = self.bot.get_channel(row[0])
            permissions = chan_left.permissions_for(chan_left.guild.me)
            if not permissions.embed_links:
                await chan_left.send(
                    f"Member {user.mention} Banned\nModerator: {moderator}\nReason: {reason}"
                )
                return
            await chan_left.send(embed=embed)



    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        Listener to member updates.

        This will post an embed in a specific channel
        when any member update his server's infos, which
        includes: nickname, roles, pending, timeout,
        server's avatar and flags.

        Args:
            None
        """
        if after.bot:
            return

        conn, cur = get_server_database(after.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("users",))
        row = cur.fetchone()
        conn.close()
        if row:
            userschanname = self.bot.get_channel(row[0])

            if userschanname:
                permissions = userschanname.permissions_for(userschanname.guild.me)
                if not permissions.embed_links:
                    return
                the_change = None
                time_zone = await get_time_zone(after.guild.id)
                embed = discord.Embed(color=0x00FF00, title="MEMBER UPDATE")
                embed.set_thumbnail(url=before.avatar)

                if before.guild_avatar != after.guild_avatar:
                    the_change = "avatar"
                    embed.set_image(url=after.guild_avatar)
                elif before.display_avatar != after.display_avatar:
                    the_change = "avatar"
                    embed.set_image(url=after.display_avatar)
                elif before.timed_out_until != after.timed_out_until:
                    the_change = "timed_out_until"
                elif before.name != after.name:
                    the_change = "name"
                elif before.display_name != after.display_name:
                    the_change = "display_name"
                elif before.nick != after.nick:
                    the_change = "nick"
                elif before.roles != after.roles:
                    the_change = "roles"
                elif before.pending != after.pending:
                    the_change = "pending"
                elif before.flags != after.flags:
                    the_change = "flags"
                else:
                    return

                formatted_change = the_change.replace("_", " ").title()

                if the_change == "roles":
                    before_roles = [role.name for role in before.roles if role.name != "@everyone"]
                    after_roles = [role.name for role in after.roles if role.name != "@everyone"]
                    before_value = (
                        f"Removed: "
                        f"{', '.join(role for role in before_roles if role not in after_roles)}"
                    )
                    after_value = (
                        "Added: "
                        f"{', '.join(role for role in after_roles if role not in before_roles)}"
                    )
                    roles_value = f"{', '.join(after_roles)}" if after_roles else ""
                    embed.add_field(
                        name=f"Change in member's {formatted_change}",
                        value=f"Member: {after.mention}\n {before_value}\n {after_value}\n "
                            f"Roles: {roles_value}", inline=False
                    )
                elif the_change == "timed_out_until":
                    if after.timed_out_until is not None:
                        formatted_time = (
                            after.timed_out_until.astimezone(time_zone).strftime("%m/%d - %H:%M")
                        )
                        embed.add_field(
                            name="Member is now in timeout",
                            value=f"Member: {after.mention}\n "
                                f"**In timeout until:** {formatted_time}", inline=False
                        )
                    else:
                        embed.add_field(
                            name="Member's timeout removed",
                            value=f"Member: {after.mention}", inline=False
                        )
                elif the_change in ("name", "nick", "pending", "flags", "display_name"):
                    before_value = getattr(before, the_change, "Unknow")
                    after_value = getattr(after, the_change, "Unknow")
                    embed.add_field(
                        name=f"Change in member's {formatted_change}",
                        value=f"Member: {after.mention}\n **Before:** {before_value}\n "
                            f"**=>After:** {after_value}", inline=False
                    )
                elif the_change == "avatar":
                    embed.set_thumbnail(url=before.guild_avatar)
                    embed.set_image(url=after.guild_avatar)
                    embed.add_field(
                        name=f"Change in member's {formatted_change}",
                        value=f"Member: {after.mention}\n", inline=False
                    )
                embed.set_footer(
                    text=f"{after.name} ({after.id})",
                    icon_url=after.avatar
                )
                embed.timestamp = datetime.now(time_zone)
                await userschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        """
        Listener to member updates.

        This will post an embed in a specific channel
        when any member update his server's infos, which
        includes: nickname, roles, pending, timeout,
        server's avatar and flags.

        Args:
            None
        """
        if after.bot:
            return
        if before.avatar == after.avatar:
            return

        for guilds in after.mutual_guilds:
            server_id = guilds.id
            conn, cur = get_server_database(server_id)
            cur.execute("SELECT id FROM setup WHERE chans = ?", ("users",))
            row = cur.fetchone()
            conn.close()

            if row:
                userschan = int(row[0])
                userschanname = self.bot.get_channel(userschan)
                permissions = userschanname.permissions_for(userschanname.guild.me)
                if not permissions.embed_links:
                    return
                embed = discord.Embed(color=0x00FF00, title="USER AVATAR UPDATE")
                embed.add_field(
                    name="New user avatar",
                    value=f"{after.mention} ({after.id})\n"
                        f"Name: {after.display_name}",
                    inline=True
                )
                embed.set_thumbnail(url=before.avatar)
                embed.set_image(url=after.avatar)
                await userschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """
        Listener to channel creation.

        This will post an embed in a specific channel
        when any channel, including voice, text and
        categories, are created. If the creation is
        in a category, the embed will show that
        category.

        Args:
            None
        """
        conn, cur = get_server_database(channel.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("audits",))
        row = cur.fetchone()
        conn.close()
        if row:
            auditschanname = self.bot.get_channel(row[0])
            permissions = auditschanname.permissions_for(auditschanname.guild.me)
            if not permissions.embed_links:
                return
            if isinstance(channel, discord.TextChannel):
                type_created = "Channel"
            elif isinstance(channel, discord.VoiceChannel):
                type_created = "Voice channel"
            elif isinstance(channel, discord.CategoryChannel):
                type_created = "Category"
            else:
                type_created = "Other channel"

            embed = discord.Embed(color=0xffffff, title=f"{type_created} updated")
            embed.add_field(
                name=f"{type_created} created",
                value=f"{channel.category} \n╚►{channel.mention} ({channel})"
            )
            await auditschanname.send(embed=embed)


    async def is_a_bot_chan(self, guild, channel):
        """
        Function that checks for database channels.

        To avoid any problem, this function will make
        sure that any deleted channel was not a part
        of it's database, such as modlogs channels.

        If the deleted channel was part of the database,
        a message will be sent to a specific channel
        letting know the mods that an important channel
        has been deleted.

        Args:
            guild
            channel
        """
        conn, cur = get_server_database(guild.id)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cur.fetchall()]

        for table_name in tables:
            cur.execute(f"PRAGMA table_info({table_name})")
            column_names = [row[1] for row in cur.fetchall()]

            if "id" in column_names:
                cur.execute(f"SELECT * FROM {table_name} WHERE id = ?", (channel.id,))
                row = cur.fetchone()
                if row:
                    cur.execute(f"DELETE FROM {table_name} WHERE id = ?", (channel.id,))
                    conn.commit()

        conn.close()


    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """
        Listener to channel deletion.

        This will post an embed in a specific channel
        when any channel, including voice, text and
        categories, are deleted. If the deletion is
        in a category, the embed will show that
        category.

        This listener is linked with the function
        is_a_bot_chan, allowing a verification if
        the channel deleted was part of the database.

        Args:
            channel
        """
        is_setup_chan = False
        conn, cur = get_server_database(channel.guild.id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("audits",))
        auditschanid = cur.fetchone()
        cur.execute("SELECT * FROM setup WHERE id = ?", (channel.id,))
        setupchan = cur.fetchall()
        if auditschanid is not None:
            if auditschanid[0] == channel.id:
                cur.execute("DELETE FROM setup WHERE id = ?", (channel.id,))
                conn.commit()
                conn.close()
                return
        if setupchan:
            cur.execute("DELETE FROM setup WHERE id = ?", (channel.id,))
            is_setup_chan = True
            conn.commit()
        conn.close()
        if auditschanid:
            auditschanname = self.bot.get_channel(auditschanid[0])
            permissions = auditschanname.permissions_for(auditschanname.guild.me)
            if not permissions.embed_links:
                return
            await self.is_a_bot_chan(channel.guild, channel)

            if isinstance(channel, discord.TextChannel):
                type_deleted = "Channel"
            elif isinstance(channel, discord.VoiceChannel):
                type_deleted = "Voice channel"
            elif isinstance(channel, discord.CategoryChannel):
                type_deleted = "Category"
            else:
                type_deleted = "Other channel"

            embed = discord.Embed(color=0xffffff, title=f"{type_deleted} updated")
            embed.add_field(
                name=f"{type_deleted} deleted",
                value=f"{channel.category} \n╚►***{channel}***"
            )
            if is_setup_chan == True:
                embed.add_field(
                    name="Setup channel deleted",
                    value=f"__**#{channel.name}**__ was the channel for {setupchan[0][0]}.\n"
                    f"{setupchan[0][1]} has been removed from the server's database.",
                    inline=False
                )
            await auditschanname.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """
        Listener to channel update.

        This will post an embed in a specific channel
        when any channel, including voice, text and
        categories, are updated. If the updated channel
        is in a category, the embed will show that
        category.

        Args:
            None
        """
        conn, cur = get_server_database(after.guild.id)
        cur.execute("SELECT * FROM servstats WHERE id = ?", (before.id,))
        rows = cur.fetchall()

        if isinstance(after, discord.TextChannel):
            type_updated = "Channel"
        elif isinstance(after, discord.VoiceChannel):
            type_updated = "Voice channel"
        elif isinstance(after, discord.CategoryChannel):
            type_updated = "Category"
        else:
            type_updated = "Other channel"

        if not rows:
            cur.execute("SELECT id FROM setup WHERE chans = ?", ("audits",))
            row = cur.fetchone()
            conn.close()
            if row:
                auditschanname = self.bot.get_channel(row[0])
                permissions = auditschanname.permissions_for(auditschanname.guild.me)
                if not permissions.embed_links:
                    return
                if before.name != after.name or before.category != after.category:
                    embed = discord.Embed(color=0xffffff, title=f"{type_updated} updated")
                    embed.add_field(name="Before", value=f"{before.category} \n╚►***{before}***")
                    embed.add_field(
                        name="After",
                        value=f"{after.category} \n╚►***{after} ({after.mention})***")
                    await auditschanname.send(embed=embed)
        else:
            conn.close()



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Modlogs(bot))
