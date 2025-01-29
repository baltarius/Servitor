# analysis.py
"""
Cog for the activity tracking

Author: Elcoyote Solitaire
"""
import os
import datetime
import shutil
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import discord

from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands, tasks
from cogs.intercogs import get_server_database, get_time_zone



class Analysis(commands.Cog, name="analysis"):
    """
    Analysis class for servers

    This class contains loops and functions
    used for analysing online activity for
    every active servers of the bot

    Commands:

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot
        self.activity_tracker.start()



    async def plot_activity(self, guild_id, time_zone, filename):
        """
        Creating image from a log file

        This function creates an image from the logs of every servers
        of the bot to show how many people are online every 15 minutes.

        Args:
            file as open(file)
        """
        timestamps = []
        onlines = []
        guild_dir = f"./analysis/{guild_id}"
        with open(filename, "r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(":")
                timestamp_str = f"{parts[0]}:{parts[1]}:{parts[2]}"
                timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                timestamps.append(timestamp)
                onlines.append(int(parts[-1]))

        plt.figure(figsize=(20, 6))
        plt.plot(timestamps, onlines)
        plt.xlabel(f"Timestamp ({time_zone})")
        plt.ylabel("Number of Online Members")
        plt.title("Server Activity Over Time")
        plt.xticks(rotation=45, ha="right")
        plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=3))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.tight_layout()
        plt.savefig(f"{guild_dir}/activity_plot.png")
        plt.close()
        diag_week = f"{guild_dir}/activity_plot.png"
        return diag_week


    async def analysis_channel(self, guild_id):
        """
        Returns the channel ID of analysis if there's one
        """
        conn, cur = get_server_database(guild_id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("analysis",))
        row = cur.fetchone()
        conn.close()
        analysis_chan_id = row[0] if row else None
        return analysis_chan_id


    async def create_backup(self, guild_id, guild_dir):
        """
        Create backup of analysis files

        Called every sunday between 00:00 and 00:15 to
        backup previous week's logs and create a new one.

        """
        backup_dir = os.path.join(guild_dir, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        time_zone = await get_time_zone(guild_id)
        current_time = datetime.datetime.now(time_zone)
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        original_file = os.path.join(guild_dir, "activity.txt")
        backup_file = os.path.join(backup_dir, f"activity_{timestamp}.txt")

        shutil.copy2(original_file, backup_file)
        with open(original_file, "w", encoding="utf-8"):
            pass

        backups = sorted(os.listdir(backup_dir))
        if len(backups) > 6:
            for old_backup in backups[:-6]:
                os.remove(os.path.join(backup_dir, old_backup))


    @tasks.loop(minutes=15)
    async def activity_tracker(self):
        """
        Loop for activity tracking

        This loop tracks online member every 15 minutes
        for every active servers of the bot.
        """
        for guild in self.bot.guilds:
            time_zone = await get_time_zone(guild.id)
            time_stamp = datetime.datetime.now(time_zone)
            timestamp = datetime.datetime.now(time_zone).strftime("%Y-%m-%d %H:%M:%S")

            wday = time_stamp.weekday()
            dhour = time_stamp.hour
            hminute = time_stamp.minute
            online_members = [
                member for member in guild.members
                if not member.bot and member.status != discord.Status.offline
            ]
            onlines = len(online_members)
            guild_dir = f"./analysis/{guild.id}"
            filename = os.path.join(guild_dir, "activity.txt")

            if not os.path.exists(guild_dir):
                os.makedirs(guild_dir)

            with open(filename, "a", encoding="utf-8") as file:
                file.write(f"{timestamp}:{onlines}\n")

            if wday == 6 and dhour == 1 and hminute < 15:
                analysis_chan_id = await self.analysis_channel(guild.id)
                diag_week = await self.plot_activity(guild.id, time_zone, filename)
                if analysis_chan_id is not None:
                    analysis_chan = self.bot.get_channel(analysis_chan_id)
                    if analysis_chan is not None:
                        await analysis_chan.send(
                            content="This is the analysis diagram for the past week for "
                            f"{guild.name}",
                            file=discord.File(diag_week)
                        )
                await self.create_backup(guild.id, guild_dir)


    @activity_tracker.before_loop
    async def before_activity_tracker(self):
        """
        Waiting for the bot to be ready
        """
        await self.bot.wait_until_ready()


    @app_commands.command(
        name="analysis",
        description="Show analysis diagram for specified week"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(week="Choose the week for the diagram")
    @app_commands.choices(week=[
        Choice(name="current week", value=1),
        Choice(name="last week", value=2),
        Choice(name="two weeks ago", value=3),
        Choice(name="three weeks ago", value=4),
        Choice(name="four weeks ago", value=5),
        Choice(name="five weeks ago", value=6)
    ])
    async def analysis(self, interaction: Interaction, week: Choice[int]):
        """
        Sends the diagram as a file to the current channel

        Creates a diagram from the selected week then
        sends it as an attachment to the current channel.

        Args:
            interaction as discord.Interaction
            week as Choice
        """
        guild = interaction.guild
        time_zone = await get_time_zone(guild.id)
        guild_dir = f"./analysis/{guild.id}"
        backup_dir = os.path.join(guild_dir, "backups")

        if week.value == 1:
            filename = os.path.join(guild_dir, "activity.txt")
            if os.path.exists(filename):
                diag = await self.plot_activity(guild.id, time_zone, filename)
                await interaction.response.send_message(
                    content=f"Here is the activity diagram for the {week.name}.",
                    file=discord.File(diag)
                )
                return

            await interaction.response.send_message(
                content="Current week log file not found.",
                ephemeral=True
            )
            return

        if not os.path.exists(backup_dir):
            await interaction.response.send_message(
                content="No backups available.",
                ephemeral=True
            )
            return

        backups = sorted(os.listdir(backup_dir), reverse=True)

        if len(backups) < week.value - 1 :
            await interaction.response.send_message(
                content=f"The selected week doesn't have any log. ({len(backups)} week(s))",
                ephemeral=True
            )
            return

        filename = os.path.join(backup_dir, backups[week.value - 2])
        diag = await self.plot_activity(guild.id, time_zone, filename)
        await interaction.response.send_message(
            content=f"Here is the activity diagram for {week.name}.",
            file=discord.File(diag)
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Analysis(bot))
