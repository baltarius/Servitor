# anniversaries.py
"""
Server anniversaries cog.

This cog is anniversaries system, allowing
members to add their anniversary and the
bot will remind the daily anniversaries in
a set channel.

Author: Elcoyote Solitaire
"""
import calendar
import datetime
import discord

from datetime import datetime
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from discord.utils import get
from discord.app_commands import Group, command
from cogs.intercogs import get_server_database, add_achievement



class Anniversaries(commands.Cog, name="anniversaries"):
    """
    Anniversaries class for servers.

    This class contains commands, automatic functions
    and loops used for the server anniversaries system.

    Commands:
        /anniv
            - hour
            - add
            - addmember
            - remove
            - list

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot
        self.anniversaires_message.start()


    async def cog_unload(self):
        self.anniversaires_message.cancel()


    def is_valid_date(self, month, day):
        """
        Function to validate a date.
        
        Verify if the month is valid and if there's 30
        or 31 days in the month (29 for february).
        
        Used by anniv_add() function.
        
        Args:
            month as int
            day as int
        """
        if month < 1 or month > 12 or day < 1 or day > 31:
            return False
        if month in [4, 6, 9, 11]:
            if day > 30:
                return False
        if month == 2:
            if day > 29:
                return False
        return True


    def has_today_anniv(self, server_id):
        """
        Function to check if there's an anniversary today.
        
        Verify if today (as datetime.now().day) has an
        entry in the server's database.
        
        Used by anniversaires_message() function (loop).
        
        Args:
            server_id
        """
        month = datetime.now().month
        day = datetime.now().day
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT id FROM anniv WHERE month = ? AND day = ?", (month, day))
        today_anniv = cur.fetchall()
        conn.close()
        anniv_ids = [row[0] for row in today_anniv]
        return anniv_ids


    def has_month_anniv(self, server_id):
        """
        Function to check if there's anniversaries this month.
        
        Verify if this month (as datetime.now().month) has
        entries in the server's database.
        
        Used by anniversaires_message() function (loop).
        
        Args:
            server_id
        """
        if datetime.now().day == 1:
            month = datetime.now().month
            conn, cur = get_server_database(server_id)
            cur.execute("SELECT * FROM anniv WHERE month = ? ORDER BY day", (month,))
            month_anniv = cur.fetchall()
            conn.close()
            return month_anniv
        return None


    def hour_chan(self, server_id):
        """
        Function to check the hour for the message.
        
        Verify the database to return the hours and the
        channel to use for the anniversaries messages.
        
        Used by anniversaires_message() function (loop).
        
        Args:
            server_id
        """
        conn, cur = get_server_database(server_id)
        cur.execute(
            "SELECT id FROM setup WHERE chans IN (?, ?) "
            "ORDER BY CASE chans WHEN ? THEN 0 ELSE 1 END",
            ("hour", "anniv", "anniv")
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return None, None
        anniv_chan = self.bot.get_channel(rows[0][0]) if rows[0][0] else None
        msg_hour = rows[1][0] if len(rows) > 1 and rows[1][0] else None
        if anniv_chan and msg_hour:
            return anniv_chan, msg_hour
        return None, None


    @tasks.loop(minutes=60)
    async def anniversaires_message(self):
        """
        Send the anniversary message every day.

        This loop runs every minute and checks if the time
        is equal to the one set for the daily message.

        Args:
            None
        """
        for guild in self.bot.guilds:
            server_id = guild.id
            anniv_chan, msg_hour = self.hour_chan(server_id)
            if msg_hour == datetime.now().hour:
                month_anniv = self.has_month_anniv(server_id)
                anniv_ids = self.has_today_anniv(server_id)
                if month_anniv:
                    embed = discord.Embed(
                        color=0xFFC0CB,
                        title=f"Anniversaries for {datetime.now().strftime('%B')}",
                        description="Coming up:"
                    )
                    for userid in month_anniv:
                        member_anniv = self.bot.get_user(userid[0])
                        if member_anniv:
                            embed.add_field(
                                name="",
                                value=f"{member_anniv.mention}: {userid[2]}", inline=False
                            )
                        else:
                            embed.add_field(
                                name="",
                                value=f"<@{userid[0]}>: {userid[2]}", inline=False
                            )
                    await anniv_chan.send(embed=embed)

                if anniv_ids:
                    embed = discord.Embed(
                        color=0xFFC0CB,
                        title=f"Anniversaries for {datetime.now().strftime('%Y-%m-%d')}",
                        description="HAPPY BIRTHDAY TO:"
                    )
                    for userid in anniv_ids:
                        member_anniv_day = self.bot.get_user(userid)
                        if not member_anniv_day:
                            member_anniv_day = f"<@{userid}>"
                        else:
                            member_anniv_day = member_anniv_day.mention
                        embed.add_field(
                            name="",
                            value=f"{member_anniv_day}", inline=False
                        )
                    await anniv_chan.send(embed=embed)


    anniv_group = Group(
        name="anniv", description="Group of command for anniversaires", guild_only=True
    )


    @anniv_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(hour="Select the hour for the message (0~23)")
    async def hour(self, interaction: Interaction, hour: int):
        """
        Change the hour of the daily message about
        members' anniversaries.

        Args:
            interaction as discord.Interaction
            hour: number of messages (integer 0~23)
        """
        if not 00 <= hour <= 23:
            await interaction.response.send_message(
                content="Please specify an hour between 00 and 23.",
                ephemeral=True
            )
            return

        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "INSERT OR REPLACE INTO setup (chans, id) VALUES (?, ?)", ("hour", hour)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"Hour for daily anniversary message is set to {hour}h.",
            ephemeral=True
        )


    @anniv_group.command()
    @app_commands.describe(month="Month 1 to 12", day="Day 1 to 31")
    @app_commands.checks.cooldown(2, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    async def add(self, interaction: Interaction, month: str, day: str):
        """
        Adds an anniversary in the database.

        Args:
            interaction as discord.Interaction
            month as str between 1 and 12
            Day as str between 1 and 31
        """
        month_names = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December"
        }
        try:
            month = int(month)
            day = int(day)
        except ValueError:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content="Month must be 1~12 and Day must be 1~31",
                ephemeral=True
            )
            return

        suffixes = ['th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th']
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = suffixes[day % 10]

        if self.is_valid_date(month, day) is True:
            user = interaction.user
            conn, cur = get_server_database(interaction.guild.id)
            cur.execute(
                "INSERT OR REPLACE INTO anniv (id, month, day) VALUES (?, ?, ?)",
                (user.id, month, day)
            )
            conn.commit()
            conn.close()
            await add_achievement(interaction.guild.id, user.id, "Happy birthday")
            await interaction.response.send_message(
                f"{user} has been added/updated to the calender "
                f"at {month_names[month]} {day}{suffix}.",
                ephemeral=True
            )

        else:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message("Please use a valid date.", ephemeral=True)


    @anniv_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        member="The member to whom you want to add the birth day",
        month="Month of birth day (1~12)",
        day="Day of birth day (1~31)"
    )
    async def addmember(
        self, interaction: Interaction, member: discord.Member, month: str, day: str
    ):
        """
        Adds an anniversary in the database.

        Args:
            interaction as discord.Interaction
            member as discord.Member
            month as str between 1 and 12
            Day as str between 1 and 31
        """
        if member.bot:
            await interaction.response.send_message(
                content="Applications don't participate to anniversary's system.",
                ephemeral=True
            )
            return
        month_names = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December"
        }
        try:
            month = int(month)
            day = int(day)
        except ValueError:
            await interaction.response.send_message(
                content="Month must be 1~12 and Day must be 1~31",
                ephemeral=True
            )
            return

        suffixes = ['th', 'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th']
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = suffixes[day % 10]

        if self.is_valid_date(month, day) is True:
            conn, cur = get_server_database(interaction.guild.id)
            cur.execute(
                "INSERT OR REPLACE INTO anniv (id, month, day) VALUES (?, ?, ?)",
                (member.id, month, day)
            )
            conn.commit()
            conn.close()
            await interaction.response.send_message(
                f"{member} has been added/updated to the calender "
                f"at {month_names[month]} {day}{suffix}.",
                ephemeral=True
            )

        else:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content="Please use a valid date.",
                ephemeral=True
            )


    @anniv_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member to be removed from the anniversaries' table")
    async def remove(self, interaction: Interaction, user: discord.Member):
        """
        Removes a member from the anniversaries' table.

        Args:
            interaction as discord.Interaction
            hour: number of messages (integer 0~23)
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "DELETE FROM anniv WHERE id = ?", (user.id,)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"Removed {user} from the anniversaries' calendar.",
            ephemeral=True
        )


    @anniv_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    async def list(self, interaction: Interaction):
        """
        Sub function of anniv.

        Shows the list of entries in the calendar.

        Args:
            interaction as discord.Interaction
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM anniv ORDER BY month, day")
        rows = cur.fetchall()
        conn.close()
        anniversaries_by_month = {}
        embed = discord.Embed(title=f"Anniversaries of {interaction.guild.name}", color=0x00ff00)
        for row in rows:
            month = row[1]
            day = row[2]
            user_id = row[0]

            if month not in anniversaries_by_month:
                anniversaries_by_month[month] = []

            anniversaries_by_month[month].append({
                "user_id": user_id,
                "day": day
            })
        for month, anniversaries in anniversaries_by_month.items():
            anniversary_list = []
            for anniversary in anniversaries:
                user_id = anniversary["user_id"]
                day = anniversary["day"]
                anniversary_list.append(f"{day} : <@{user_id}>")

            anniversary_str = "\n".join(anniversary_list)

            embed.add_field(
                name=calendar.month_name[month],
                value=anniversary_str,
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @add.error
    async def add_error(self, interaction, error):
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


    @addmember.error
    async def addmember_error(self, interaction, error):
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


    @hour.error
    async def hour_error(self, interaction, error):
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


    @remove.error
    async def remove_error(self, interaction, error):
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


    @list.error
    async def list_error(self, interaction, error):
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
    await bot.add_cog(Anniversaries(bot))
