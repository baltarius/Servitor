# intercogs.py
"""
Functions use through the bot.

This file is to store every functions that are used through the entire bot.
The main function here is get_server_database.

Author: Elcoyote Solitaire
"""
import sqlite3
import pytz
import discord

from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Choice



class Intercogs(commands.Cog, name="intercogs"):
    """
    Intercogs class for utilities.

    This class contains utility to be used through the bot's cogs.
    Empty for now.
    
    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot


    # USING THIS METHOD ALLOWS THE ADMIN TO ADD/CHANGE TABLES FROM
    # THE DATABASE WITHOUT HAVING TO FIND WHERE TO APPLY THE CHANGES.
    # IT ALSO ALLOWS TO CREATE ALL NECESSARY TABLES AT ONCE EVERYTIME
    # A BOT JOINS A SERVER. EVERYTHING THAT TRIGGERS A SEARCH/WRITE IN
    # THE DATABASE WILL AUTOMATICALLY GO THROUGH THIS.

    def get_server_database(self, server_id):
        """
        Main function to obtain servers' database.
        Creates all the necessary tables if they aren't created yet.

        Args:
            server_id as guild.id
        """
        db_file = f"./database/servers/{server_id}.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        cur.execute('''CREATE TABLE IF NOT EXISTS stats
            (id INTEGER PRIMARY KEY,
            messages INTEGER,
            words INTEGER,
            characters INTEGER,
            emojis INTEGER,
            reactions INTEGER,
            edited INTEGER,
            deleted INTEGER,
            jvoice INTEGER,
            tvoice INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS setup
            (chans TEXT PRIMARY KEY,
            id INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS level
            (id INTEGER PRIMARY KEY,
            exp INTEGER,
            level INTEGER,
            total INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS reaction
            (message INTEGER,
            emoji TEXT,
            type TEXT,
            role INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS servstats
            (chans TEXT PRIMARY KEY,
            id INTEGER,
            region TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS suggestion
            (number INTEGER PRIMARY KEY AUTOINCREMENT,
            id INTEGER,
            authorid INTEGER,
            decision TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS exception
            (id INTEGER,
            reason TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS punishment
            (target INTEGER,
            starters INTEGER,
            message INTEGER,
            channel INTEGER,
            PRIMARY KEY (target, starters))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS anniv
            (id INTEGER PRIMARY KEY,
            month INTEGER,
            day INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS voice
            (id INTEGER PRIMARY KEY,
            jtime TIMESTAMP,
            embmsg INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS timezone
            (id INTEGER PRIMARY KEY,
            timezone TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS achievements
            (id INTEGER,
            achievements TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS notes
            (number INTEGER PRIMARY KEY AUTOINCREMENT,
            authorid INTEGER,
            ctime TIMESTAMP,
            note TEXT,
            active TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS achievecount
            (id INTEGER,
            achieve TEXT,
            count INTEGER,
            notes TEXT,
            PRIMARY KEY (id, achieve))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS fightgame
            (attackid INTEGER,
            opponentid INTEGER,
            attack1 INTEGER,
            attack2 INTEGER,
            attack3 INTEGER,
            defense1 INTEGER,
            defense2 INTEGER,
            defense3 INTEGER,
            PRIMARY KEY (attackid, opponentid))''')

        cur.execute('''CREATE TABLE IF NOT EXISTS fightscore
            (id INTEGER,
            score INTEGER,
            games INTEGER)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS anonyme
            (id INTEGER PRIMARY KEY,
            prefix TEXT,
            suffix TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS member_options
            (id INTEGER PRIMARY KEY,
            single_hug TEXT,
            anon_hug TEXT,
            group_hug TEXT,
            fight TEXT,
            kiss TEXT)''')

        conn.commit()
        return conn, cur


    # exception function to update the table is in the modlogs.py
    def is_exception(self, server_id, channel_id, reason):
        """
        Verify if the channel is in the exception's list.

        Args:
            server_id as guild.id
            channel_id as TextChannel.id
            reason as a string - The specific reason to be an exception.
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute("SELECT * FROM exception WHERE id = ? AND reason = ?", (channel_id, reason))
        row = cur.fetchone()
        conn.close()
        if row:
            return True
        return False


    async def add_achievement(self, server_id, user_id, achievement):
        """
        Adds an achievement to a user.
        
        Verify if the user has the achievement and applies if it doesn't.
        
        Args:
            server_id as guild.id
            user_id as user.id
            achievement as str
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute("SELECT * FROM achievements WHERE id = ?", (user_id,))
        rows = cur.fetchall()
        if not rows:
            cur.execute(
                "INSERT INTO achievements (id, achievements) VALUES (?, ?)", (user_id, achievement)
            )
            conn.commit()
            conn.close()
            return
        for row in rows:
            if achievement in row:
                conn.close()
                return
        cur.execute(
            "INSERT INTO achievements (id, achievements) VALUES (?, ?)", (user_id, achievement)
        )
        conn.commit()
        conn.close()


    async def add_achievecount(self, server_id, user_id, achievement):
        """
        Adds a count to an achievement for a user.
        
        Verify if the user has the achievement and applies if it doesn't.
        
        Args:
            server_id as guild.id
            user_id as user.id
            achievement as str
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute(
            "SELECT * FROM achievecount WHERE id = ? AND achieve = ?", (user_id, achievement)
        )
        rows = cur.fetchall()
        if rows:
            count = int(rows[0][2]) + 1
            cur.execute(
                "UPDATE achievecount SET count = ? WHERE id = ? AND achieve = ?",
                (count, user_id, achievement)
            )
        else:
            count = 1
            cur.execute(
                "INSERT INTO achievecount (id, achieve, count) VALUES (?, ?, ?)",
                (user_id, achievement, count)
            )
        conn.commit()
        conn.close()
        return count


    async def get_achievements(self, server_id, user_id):
        """
        Retrieves the achievements of a user from a specific server.
        
        Uses the user ID to find all achievements related to that user
        in the server's database. Also returns the total amount of achievements.
        
        Args:
            server_id as guild.id
            user_id as user.id
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute("SELECT * FROM achievements WHERE id = ?", (user_id,))
        row = cur.fetchall()
        conn.close()
        if not row:
            return None, None, None, 0
        achievements = []
        for row in row:
            achievements.append(row[1])

        if len(achievements) > 10:
            achievements_1 = achievements[:10]
            achievements_2 = achievements[10:]
        else:
            achievements_1 = achievements
            achievements_2 = []

        liste_1 = '\n'.join(achievements_1)
        liste_2 = '\n'.join(achievements_2)

        total_achieves = len(achievements)
        return achievements, liste_1, liste_2, total_achieves


    async def get_time_zone(self, server_id):
        """
        Retrieve the timezone for the server.

        Args:
            server_id: The ID of the server.
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute("SELECT timezone FROM timezone")
        row = cur.fetchone()
        conn.close()
        time_zone = pytz.timezone(row[0]) if row is not None else pytz.timezone("US/Eastern")
        return time_zone


    async def check_senority(self, date_joined, delay: int):
        """
        Checks between senority and a given delay

        Allows commands to verify if a user has an X amount of
        senority on the server before being able to use commands.

        Args:
            date_joined as discord.user.joined_at
            delay as int for the amount of hours required

        Returns:
            Boolean: True if user has reached the delay
        """
        cdate = datetime.utcnow().replace(tzinfo=timezone.utc)
        diff = cdate - date_joined
        senority = False
        if diff > timedelta(hours=delay):
            senority = True
        return senority


    async def check_optin(self, server_id, user_id, system):
        """
        Checks if the user is opt-in for systems

        Allows commands to verify if the targeted member
        is opt-in or opt-out for the different systems.

        Args:
            user_id as discord.User.id
            system as str for colum in member_options table
        """
        conn, cur = self.get_server_database(server_id)
        cur.execute(f"SELECT {system} FROM member_options WHERE id = ?", (user_id,))
        result = cur.fetchone()
        conn.close()
        if result:
            if result[0] == "off":
                return False
        return True


    @app_commands.command(
        name="showsetup",
        description="Shows channels from setup's table"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def showsetup(self, interaction: Interaction):
        """
        Request all infos from setup table in database.

        This command will create an embed with all info
        from the setup's table in the server's database.

        Arguments:
            interaction as discord.Interaction.
        """
        conn, cur = self.get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM setup")
        rows = cur.fetchall()
        conn.close()

        setup_channels = [
            "audits", "edits", "users", "joins", "lefts", "alerts",
            "logs", "level", "starboard", "analysis", "vote",
            "welcome", "ticket", "voices", "anniv", "fight"
        ]
        setup_roles = [
            "Level 10", "Level 20", "Level 30", "Level 40", "Level 50",
            "Level 60", "Level 70", "Level 80", "Level 90", "Level 100"
        ]
        embed = discord.Embed(
            color=0xFFC0CB,
            title=f"List of the setup for {interaction.guild.name}",
            description="Setup: Channel"
        )
        for chan in rows:
            if chan[0] in setup_channels:
                embed.add_field(
                    name="",
                    value=f"{chan[0]}: <#{chan[1]}>\n", inline=False
                )
            elif chan[0] in setup_roles:
                embed.add_field(
                    name="",
                    value=f"{chan[0]}: <@&{chan[1]}>\n", inline=False
                )
            else:
                embed.add_field(
                    name="",
                    value=f"{chan[0]}: {chan[1]}\n", inline=False
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @showsetup.error
    async def showsetup_error(self, interaction, error):
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
        name="exception",
        description="Adds channel as exception"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        addremove="Add or remove a channel",
        channel="Choose a text channel",
        exceptiontype="Choose an exception type"
    )
    @app_commands.choices(addremove=[
        Choice(name="add", value=1),
        Choice(name="remove", value=2)
    ])
    @app_commands.choices(exceptiontype=[
        Choice(name="exp", value=1),
        Choice(name="delete", value=2)
    ])
    async def exception(
        self, interaction: Interaction, addremove: Choice[int],
        channel: discord.TextChannel, exceptiontype: Choice[int]
    ):
        """
        Adds channel as an exception to the database.

        This command will create an entry for a TextChannel
        in the database for further restrictions/exceptions.
        
        Example:
            /exception add #admins delete
            /exception add #bots exp
            /exception remove #general exp

        Arguments:
            interaction as discord.Interaction
            addremove as Choice between add and remove
            channel as discord.TextChannel
            exceptiontype as Choice between exp, delete, command
            
        Parameters:
            exp: Restrict the channel from giving exp to users typing there.
            delete: Deleting/editing messages won't trigger the modlogs.
        """
        conn, cur = self.get_server_database(interaction.guild.id)
        if addremove.name == "add":
            cur.execute(
                "INSERT OR REPLACE INTO exception (id, reason) VALUES (?, ?)",
                (channel.id, exceptiontype.name)
            )
            await interaction.response.send_message(
                content=f"{channel.mention} has been set as {exceptiontype.name}.",
                ephemeral=True
            )

        else:
            cur.execute(
                "DELETE FROM exception WHERE id = ? AND reason = ?", (channel.id, exceptiontype.name)
            )
            await interaction.response.send_message(
                content=f"{channel.mention} has been removed from the list of "
                f"{exceptiontype.name} exception",
                ephemeral=True
            )

        conn.commit()
        conn.close()


    @exception.error
    async def exception_error(self, interaction, error):
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
        name="settimezone",
        description="Set the timezone"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(timezonegmt="Choose a timezone for the server")
    @app_commands.choices(timezonegmt=[
        Choice(name="Pacific/Midway", value=1),
        Choice(name="Pacific/Honolulu", value=2),
        Choice(name="Pacific/Marquesas", value=3),
        Choice(name="Pacific/Gambier", value=4),
        Choice(name="US/Alaska", value=5),
        Choice(name="America/Edmonton", value=6),
        Choice(name="America/Chicago", value=7),
        Choice(name="America/New_York", value=8),
        Choice(name="America/Goose_Bay", value=9),
        Choice(name="Atlantic/South_Georgia", value=10),
        Choice(name="Atlantic/Cape_Verde", value=11),
        Choice(name="GMT", value=12),
        Choice(name="Europe/Dublin", value=13),
        Choice(name="Europe/Paris", value=14),
        Choice(name="Europe/Moscow", value=15),
        Choice(name="Asia/Dubai", value=16),
        Choice(name="Asia/Tehran", value=17),
        Choice(name="Asia/Samarkand", value=18),
        Choice(name="Asia/Dhaka", value=19),
        Choice(name="Asia/Bangko", value=20),
        Choice(name="Asia/Hong_Kong", value=21),
        Choice(name="Asia/Seoul", value=22),
        Choice(name="Australia/Brisbane", value=23),
        Choice(name="Pacific/Norfolk", value=24),
        Choice(name="Pacific/Fiji", value=25)
    ])
    async def settimezone(
        self, interaction: Interaction, timezonegmt: Choice[int]
    ):
        """
        Set the timezone for the server.

        This command add an entry in the database to
        set the main timezone of the server.

        Example:
            /set-timezone Choice

        Arguments:
            interaction as discord.Interaction
            timezonegmt as Choice[int]
        """
        conn, cur = self.get_server_database(interaction.guild.id)
        cur.execute(
            "INSERT OR REPLACE INTO timezone (id, timezone) VALUES (?, ?)",
            (interaction.guild.id, timezonegmt.name,)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"Your timezone has been set as {timezonegmt.name}.", ephemeral=True
        )


    @settimezone.error
    async def settimezone_error(self, interaction, error):
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
        name="achievements",
        description="Shows your own achievements with description"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def achievements(self, interaction: Interaction):
        """
        Retrieves the achievements for the command's user.

        Retrieves the list of the achievements for the user using
        the command get_achievements(), then shows the description
        for each of the user's achievements without spoiling every
        other achievements available. Each user will be asked to
        keep the achievements secret to keep those a thrill to get.
        
        Args:
            interaction as discord.Interaction
        """
        achievements, _, _, total_achieves = (
            await self.get_achievements(interaction.guild.id, interaction.user.id)
        )
        achieves_with_desc = []
        if achievements:
            achieves_with_desc = [
                self.desc_achieves.get(achievement, achievement)
                for achievement in achievements
            ]
            liste_descr = "\n".join(achieves_with_desc)
        else:
            liste_descr = "\nNo achievement"
        await interaction.response.send_message(
            content=f"Your achievements ({total_achieves}):\n{liste_descr}\n"
                "\nPlease keep those informations a secret to keep this system entertaining.",
            ephemeral=True
        )


    @achievements.error
    async def achievements_error(self, interaction, error):
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


    @app_commands.command(
        name="achieveboard",
        description="Leaderboard for achievements"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def achieveboard(self, interaction: Interaction):
        """
        Leaderboard for level.

        Display the leaderboard of the server for
        the top 10 of the level system.

        Args:
            interaction as discord.Interaction
        """
        permissions = interaction.channel.permissions_for(interaction.channel.guild.me)
        if not permissions.embed_links:
            await interaction.response.send_message(
                content="I don't have the permissions to send embed in "
                f"{interaction.channel.mention}",
                ephemeral=True
            )
            return
        conn, cur = self.get_server_database(interaction.guild.id)

        cur.execute(
            "SELECT id, COUNT(*) as num_achievements FROM achievements GROUP BY id"
        )
        topachieve = cur.fetchall()
        conn.close()

        embed = discord.Embed(title=f"Achieveboard of {interaction.guild.name}", color=0x00ff00)
        embed.set_thumbnail(url=interaction.guild.icon)

        sorted_rows = sorted(topachieve, key=lambda x: x[1], reverse=True)[:10]
        for item in sorted_rows:
            member = self.bot.get_user(int(item[0]))
            if member is not None:
                member = member.display_name
            else:
                member = f"<@{item[0]}>"
            embed.add_field(
                name=f"{member}: {item[1]}",
                value="",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


    @achieveboard.error
    async def achieveboard_error(self, interaction, error):
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
        name="setchan",
        description="Set log channel in database"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        addremove="Add or remove a channel",
        logtype="Choose the type of log",
        channel="Choose the text channel for the log type"
    )
    @app_commands.choices(addremove=[
        Choice(name="add", value=1),
        Choice(name="remove", value=2)
    ])
    @app_commands.choices(logtype=[
        Choice(name="audits", value=1),
        Choice(name="edits", value=2),
        Choice(name="users", value=3),
        Choice(name="joins", value=4),
        Choice(name="lefts", value=5),
        Choice(name="alerts", value=6),
        Choice(name="level", value=7),
        Choice(name="starboard", value=8),
        Choice(name="vote", value=9),
        Choice(name="welcome", value=10),
        Choice(name="ticket", value=11),
        Choice(name="logs", value=12),
        Choice(name="voices", value=13),
        Choice(name="anniv", value=14),
        Choice(name="fight", value=15),
        Choice(name="analysis", value=16)
        # PLEASE MODIFY /SETALLLOGS CODE IF YOU MODIFY THIS PART
    ])
    async def setchan(
        self, interaction: Interaction, addremove: Choice[int],
        logtype: Choice[int], channel: discord.TextChannel
    ):
        """
        Function that setup database channels.

        This function is used to create entries in the
        database for every logs channels available.

        Args:
            interaction as discord.Interaction
            addremove as a Choice between add and remove
            logtype as a Choice of setup
            channel as discord.TextChannel
        """
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.embed_links:
            await interaction.response.send_message(
                content=f"I don't have the permissions to send embed in {channel.mention}",
                ephemeral=True
            )
            return

        conn, cur = self.get_server_database(interaction.guild.id)

        if addremove.name == "add":
            cur.execute(
                "INSERT OR REPLACE INTO setup (chans, id) VALUES (?, ?)",
                (logtype.name, channel.id)
            )

            await interaction.response.send_message(
                content=f"{channel.mention} has been set as ***{logtype.name}***.",
                ephemeral=True
            )

        else:
            cur.execute("DELETE FROM setup WHERE chans = ?", (logtype.name,))
            await interaction.response.send_message(
                content=f"{channel.mention} has been removed from setup as {logtype.name}",
                ephemeral=True
            )
        conn.commit()
        conn.close()


    @setchan.error
    async def setchan_error(self, interaction, error):
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
        name="setalllogs",
        description="Set all logs to a single chan"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Choose the channel that will receive ALL the mod logs")
    async def setalllogs(self, interaction: Interaction, channel: discord.TextChannel):
        """
        Function that setup database channels.

        This function is used to create entries in the
        database for every logs channels in a single channel.

        Args:
            interaction as discord.Interaction
            channel as discord.TextChannel
        """
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.embed_links:
            await interaction.response.send_message(
                content="Please give me the permission to send embed messages in "
                f"{channel.mention}",
                ephemeral=True
            )
            return
        conn, cur = self.get_server_database(interaction.guild.id)
        logtypes = [
            "audits", "edits", "users", "joins", "lefts", "alerts", "logs", "level", "starboard",
            "vote", "welcome", "ticket", "voices", "anniv", "fight", "analysis"
        ]
        for logtype in logtypes:
            cur.execute(
                "INSERT OR REPLACE INTO setup (chans, id) VALUES (?, ?)", (logtype, channel.id)
            )
        conn.commit()
        await interaction.response.send_message(
            content=f"{channel.mention} has been set for all the logs.",
            ephemeral=True
        )
        conn.close()


    @setalllogs.error
    async def setalllogs_error(self, interaction, error):
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
        name="member_option",
        description="Select if you want to be part of the different functions of the bot."
    )
    @app_commands.guild_only()
    @app_commands.describe(option="Choose a system to opt in/out")
    @app_commands.choices(option=[
        Choice(name="all hugs", value=1),
        Choice(name="hug", value=2),
        Choice(name="anonymous hug", value=3),
        Choice(name="group hug", value=4),
        Choice(name="fight", value=5),
        Choice(name="all systems", value=6)
    ])
    @app_commands.choices(on_off=[
        Choice(name="on", value=1),
        Choice(name="off", value=2)
    ])
    async def member_option(
        self, interaction: Interaction, option: Choice[int], on_off: Choice[int]
    ):
        """
        Turns on or off systems for a member

        Allows a member to turn off systems so other
        members can use those systems on the member.

        Args:
            option as Choice for the systems
            on_off as choice for on or off
        """
        systems = {
            "hug": "single_hug",
            "anonymous hug": "anon_hug",
            "group hug": "group_hug",
            "fight": "fight"
        }
        conn, cur = self.get_server_database(interaction.guild.id)
        if option.value != 1 and option.value != 6:
            sys_opt = systems.get(option.name)
            cur.execute(
                f"INSERT INTO member_options (id, {sys_opt}) VALUES (?, ?)"
                f"ON CONFLICT(id) DO UPDATE SET {sys_opt} = EXCLUDED.{sys_opt}",
                (interaction.user.id, on_off.name)
            )
            conn.commit()
            conn.close()
        else:
            if option.value == 1:
                cur.execute(
                    """
                    INSERT INTO member_options (id, single_hug, anon_hug, group_hug)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE 
                    SET single_hug = EXCLUDED.single_hug,
                        anon_hug = EXCLUDED.anon_hug,
                        group_hug = EXCLUDED.group_hug
                    """,
                    (interaction.user.id, on_off.name, on_off.name, on_off.name)
                )
                conn.commit()
                conn.close()
            else:
                cur.execute(
                    "INSERT OR REPLACE INTO member_options"
                    "(id, single_hug, anon_hug, group_hug, fight) VALUES (?, ?, ?, ?, ?)",
                    (interaction.user.id, on_off.name, on_off.name, on_off.name, on_off.name)
                )
                conn.commit()
                conn.close()
                await interaction.response.send_message(
                    content=f"__**All systems**__ options have been switched to"
                    f"__**{on_off.name}**__",
                    ephemeral=True
                )
                return

        await interaction.response.send_message(
            content=f"You have switched __**{option.name}**__'s system to __**{on_off.name}**__.",
            ephemeral=True
        )


intercogs_instance = Intercogs(None)


def get_server_database(server_id):
    """
    Mirror function to be imported in other cogs.
    """
    return intercogs_instance.get_server_database(server_id)


async def add_achievement(server_id, user_id, achievement):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.add_achievement(server_id, user_id, achievement)


async def get_achievements(server_id, user_id):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.get_achievements(server_id, user_id)


def is_exception(server_id, channel_id, reason):
    """
    Mirror function to be imported in other cogs.
    """
    return intercogs_instance.is_exception(server_id, channel_id, reason)


async def add_achievecount(server_id, user_id, achievement):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.add_achievecount(server_id, user_id, achievement)


async def get_time_zone(server_id):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.get_time_zone(server_id)


async def check_senority(date_joined, delay: int):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.check_senority(date_joined, delay)


async def check_optin(server_id, user_id, system):
    """
    Mirror function to be imported in other cogs.
    """
    return await intercogs_instance.check_optin(server_id, user_id, system)



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Intercogs(bot))
