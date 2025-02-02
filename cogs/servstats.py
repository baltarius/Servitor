# servstats.py
"""
Server statistics cog.

This cog is for server statistics (displayed as voice channel)
The stats include a clock that can show any timezone but also
how many members, users, bots, categories, channels and roles
are present on the server.

Author: Elcoyote Solitaire
"""
import datetime
import asyncio
import discord

from datetime import datetime, time, timedelta
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.utils import get
from cogs.intercogs import get_server_database, get_time_zone, add_achievement

# add checks for permissions to manage roles, channels and permissions

class Servstats(commands.Cog, name="servstats"):
    """
    Statistics class for server.

    This class contains commands, automatic functions
    and loops used for the server statistics system.

    Task loop:
        channel_name_updater()

    Command:
        /createservstats
    """
    def __init__(self, bot):
        self.bot = bot
        self.channel_name_updater.start()


    @app_commands.command(
        name="createservstats",
        description="Creates server stats channels"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.bot_has_permissions(
        manage_roles=True,
        manage_permissions=True,
        manage_channels=True
    )
    async def createservstats(self, interaction: Interaction):
        """
        Automation functions for server stats.

        This will create everything necessary to display the stats,
        which includes database entries, categories and channels.

        Args:
            interaction as discord.Interaction
        """
        guild = interaction.guild
        conn, cur = get_server_database(guild.id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)
        }
        time_zone = await get_time_zone(interaction.guild.id)
        clock_channel = await guild.create_voice_channel(
            name=f"Local: {datetime.now(time_zone).strftime('%H:%M')}",
            position=0, overwrites=overwrites)
        cur.execute("SELECT * FROM servstats WHERE chans = ?", ("clock",))
        existing_row = cur.fetchone()
        if existing_row:
            cur.execute(
                "UPDATE servstats SET id = ?, region = ? WHERE chans = ?",
                (clock_channel.id, "America/Montreal", "clock")
            )
        else:
            cur.execute(
                "INSERT INTO servstats (chans, id, region) VALUES(?, ?, ?)",
                ("clock", clock_channel.id, "America/Montreal")
            )

        # stats [members, users, bots, categories, channels, roles]
        bot_count = sum(member.bot for member in guild.members)
        channel_count = len([
            channel for channel in guild.channels if not isinstance(
                channel, discord.CategoryChannel
            )
        ])
        user_count = guild.member_count - bot_count

        stats_cat = await guild.create_category(
            name="📊 Server Stats 📊", overwrites=overwrites, position=99
        )

        category_count = len([
            channel for channel in guild.channels if isinstance(channel, discord.CategoryChannel)
        ])

        members_channel = await guild.create_voice_channel(
            name=f"[Members]: {guild.member_count}", category=stats_cat, overwrites=overwrites
        )
        users_channel = await guild.create_voice_channel(
            name=f"[Users]: {user_count}", category=stats_cat, overwrites=overwrites
        )
        bots_channel = await guild.create_voice_channel(
            name=f"[Bots]: {bot_count}", category=stats_cat, overwrites=overwrites
        )
        category_channel = await guild.create_voice_channel(
            name=f"[Categories]: {category_count}", category=stats_cat, overwrites=overwrites
        )
        channels_channel = await guild.create_voice_channel(
            name=f"[Channels]: {channel_count}", category=stats_cat, overwrites=overwrites
        )
        roles_channel = await guild.create_voice_channel(
            name=f"[Roles]: {len(guild.roles)}", category=stats_cat, overwrites=overwrites
        )

        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("members", members_channel.id)
        )
        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("users", users_channel.id)
        )
        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("bots", bots_channel.id)
        )
        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("categories", category_channel.id)
        )
        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("channels", channels_channel.id)
        )
        cur.execute(
            "INSERT OR REPLACE INTO servstats (chans, id) VALUES(?, ?)",
            ("roles", roles_channel.id)
        )

        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content="The channels for the server's stats have been created.",
            ephemeral=True
        )
        return {
            "clock_channel": clock_channel,
            "members_channel": members_channel,
            "users_channel": users_channel,
            "bots_channel": bots_channel,
            "category_channel": category_channel,
            "channels_channel": channels_channel,
            "roles_channel": roles_channel
        }


    async def wait_until_next_quarter(self):
        """
        Delays the channel_name_updater's loop until the
        next quarter of the hour (00, 15, 30 or 45)
        """
        now = datetime.utcnow()
        next_quarter = now + timedelta(minutes=(15 - now.minute % 15))
        next_quarter = next_quarter.replace(second=0, microsecond=0)

        await asyncio.sleep((next_quarter - now).total_seconds())



    @tasks.loop(minutes=15)
    async def channel_name_updater(self):
        """
        Updates the name of the channels of the stats system.

        This loop runs every minute and checks if the time is a multiple
        of 15 minutes for the clock and 30 minutes for the other stats.

        Args:
            None
        """
        if datetime.now().minute % 15 == 0:
            for guild in self.bot.guilds:
                conn, cur = get_server_database(guild.id)
                cur.execute("SELECT id FROM servstats WHERE chans = ?", ("clock",))
                result = cur.fetchone()
                channame = self.bot.get_channel(result[0]) if result is not None else None
                conn.close()
                if channame:
                    try:
                        await channame.edit(
                            name=f"local: {datetime.now().strftime('%H:%M')}"
                        )
                    except discord.Forbidden:
                        print(f"Error: Forbidden to edit channel name in guild {guild.name}")
                    except Exception as err_edit:
                        print(f"Error updating channel name: {err_edit}")

            if datetime.now().minute % 30 == 0:
                for guild in self.bot.guilds:
                    conn, cur = get_server_database(guild.id)
                    cur.execute(
                        "SELECT * FROM servstats WHERE chans IN (?, ?, ?, ?, ?, ?)",
                        ("members", "users", "bots", "categories", "channels", "roles")
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if len(rows) >= 6:
                        channel_ids = {row[0]: row[1] for row in rows}

                        bot_count = sum(member.bot for member in guild.members)
                        user_count = guild.member_count - bot_count
                        channel_count = len([
                            channel for channel in guild.channels if not isinstance(
                                channel, discord.CategoryChannel
                            )
                        ])
                        category_count = len([
                            channel for channel in guild.channels if isinstance(
                                channel, discord.CategoryChannel
                            )
                        ])

                        chan_mem_name = self.bot.get_channel(int(channel_ids.get("members")))
                        if int(chan_mem_name.name.split(": ")[1]) != guild.member_count:
                            await chan_mem_name.edit(name=f'[Members]: {guild.member_count}')

                        chan_users_name = self.bot.get_channel(int(channel_ids.get("users")))
                        if int(chan_users_name.name.split(": ")[1]) != user_count:
                            await chan_users_name.edit(name=f'[Users]: {user_count}')

                        chan_bots_name = self.bot.get_channel(int(channel_ids.get("bots")))
                        if int(chan_bots_name.name.split(": ")[1]) != bot_count:
                            await chan_bots_name.edit(name=f'[Bots]: {bot_count}')

                        chan_cats_name = self.bot.get_channel(int(channel_ids.get("categories")))
                        if int(chan_cats_name.name.split(": ")[1]) != category_count:
                            await chan_cats_name.edit(name=f'[Categories]: {category_count}')

                        chan_chans_name = self.bot.get_channel(int(channel_ids.get("channels")))
                        if int(chan_chans_name.name.split(": ")[1]) != channel_count:
                            await chan_chans_name.edit(name=f'[Channels]: {channel_count}')

                        chan_roles_name = self.bot.get_channel(int(channel_ids.get("roles")))
                        if int(chan_roles_name.name.split(": ")[1]) != len(guild.roles):
                            await chan_roles_name.edit(name=f'[Roles]: {len(guild.roles)}')


    @channel_name_updater.before_loop
    async def before_channel_name_updater(self):
        """
        Function waiting for bot to be ready and time to be a quarter.

        Allows the bot to be ready before starting the loop and
        starts once the time is at a quarter (00, 15, 30 or 45).

        Args:
            None
        """
        await self.bot.wait_until_ready()
        await self.wait_until_next_quarter()



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Servstats(bot))
