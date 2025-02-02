# notes.py
"""
Cog regrouping everything necessary for the notes system.

The cog contains all the parameters, classes and functions
to allow server admins to add, edit, notes from the
list of notes for the server.

Author: Elcoyote Solitaire
"""
import datetime
import discord

from datetime import datetime
from discord import app_commands, Interaction
from discord.app_commands import Group, Choice
from discord.ext import commands
from cogs.intercogs import get_server_database, add_achievement



class Notes(commands.Cog, name="notes"):
    """
    Notes class for the notes system.

    This class contains commands and tools
    to allow server admins to create notes
    in the server's database.

    Commands:
        /note
            - add
            - show
            - showtext
            - update
    """
    def __init__(self, bot):
        self.bot = bot


    note_group = Group(
        name="note", description="Group of command for the server's notes", guild_only=True
    )

    @note_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(note="Enter the note you want to add to the notes")
    async def add(self, interaction: Interaction, note: str):
        """
        Add a note into the server's database. 

        The number for the note is automatic and incremental.

        Args:
            interaction as discord.Interaction
            note as a string for the note to add
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "INSERT INTO notes (authorid, ctime, note, active) VALUES (?, ?, ?, ?)",
            (interaction.user.id, datetime.now(), note, "active")
        )
        conn.commit()
        cur.execute("SELECT MAX(number) FROM notes")
        number = cur.fetchone()[0]
        conn.close()
        await interaction.response.send_message(
            f"**Note #{number} added:**\nNote: {note}",
            ephemeral=True
        )


    @note_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(notetype="Choose the notes to show")
    @app_commands.choices(notetype=[
        Choice(name="all", value=1),
        Choice(name="active", value=2),
        Choice(name="pending", value=3),
        Choice(name="open", value=4),
        Choice(name="done", value=5)
    ])
    async def show(self, interaction: Interaction, notetype: Choice[int]):
        """
        Shows the notes for a selected type

        Args:
            interaction as discord.Interaction
            notetype as Choice[int] (all, active, pending, done)
        """
        conn, cur = get_server_database(interaction.guild.id)
        if notetype.name == "all":
            cur.execute("SELECT * FROM notes")
            no_rows = "There's no note in the database."
        elif notetype.name == "open":
            cur.execute("SELECT * FROM notes WHERE active IN (?, ?)", ("active", "pending"))
            no_rows = "There's no open note (active or pending) in the database."
        else:
            cur.execute("SELECT * FROM notes WHERE active = ?", (notetype.name,))
            no_rows = f"There's no *{notetype.name}* note in the database."
        rows = cur.fetchall()
        conn.close()
        if not rows:
            await interaction.response.send_message(content=no_rows, ephemeral=True)
            return
        embed = discord.Embed(
            color=0xFFFFFF,
            title=f"{notetype.name.capitalize()} notes for "
                f"{interaction.guild.name}",
            description=""
        )
        for row in rows[:9]:
            create_time = datetime.strptime(row[2], '%Y-%m-%d %H:%M:%S.%f')
            embed.add_field(
                name=f"Note {row[0]} ({row[4]})",
                value=f"Created by: <@{row[1]}>\n"
                f"{create_time.strftime('%Y-%m-%d %H:%M:%S')}\n{row[3]}",
                inline=True
            )
        if len(rows) > 9:
            embed.set_footer(
                text=f"There's more than 9 notes for the status asked ({len(rows)} notes).\n"
                    "Please choose a specific status for the notes or use /note showtext"
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @note_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(notetype="Choose the notes to show")
    @app_commands.choices(notetype=[
        Choice(name="all", value=1),
        Choice(name="active", value=2),
        Choice(name="pending", value=3),
        Choice(name="open", value=4),
        Choice(name="done", value=5)
    ])
    async def showtext(self, interaction: Interaction, notetype: Choice[int]):
        """
        Shows the notes as a text file for a selected type

        Args:
            interaction as discord.Interaction
            notetype as Choice[int] (all, active, pending, done)
        """
        conn, cur = get_server_database(interaction.guild.id)
        if notetype.name == "all":
            cur.execute("SELECT * FROM notes")
            no_rows = "There's no note in the database."
        elif notetype.name == "open":
            cur.execute("SELECT * FROM notes WHERE active IN (?, ?)", ("active", "pending"))
            no_rows = "There's no open note (active or pending) in the database."
        else:
            cur.execute("SELECT * FROM notes WHERE active = ?", (notetype.name,))
            no_rows = f"There's no *{notetype.name}* note in the database."
        rows = cur.fetchall()
        if not rows:
            conn.close()
            await interaction.response.send_message(
                content=no_rows, ephemeral=True
            )
            return
        note_list = ""
        for row in rows:
            member = self.bot.get_user(row[1])
            if member is not None:
                author = member.display_name
            else:
                author = f"<@{row[1]}>"
            note_list += f"\n#{row[0]} ({row[4]}) by {author}: {row[3]}"

        filename = f"{interaction.guild.id}_{notetype.name}_notes.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(note_list)
        await interaction.response.send_message(
            content=f"Here's the note with status {notetype.name}",
            file=discord.File(filename),
            ephemeral=True
        )


    @note_group.command()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(notetype="Change the status for a suggestion")
    @app_commands.choices(notetype=[
        Choice(name="active", value=1),
        Choice(name="pending", value=2),
        Choice(name="done", value=3)
    ])
    async def update(self, interaction: Interaction, note: int, notetype: Choice[int]):
        """
        Changes the status of a note

        Args:
            interaction as discord.Interaction
            note as int for the note's number
            notetype as Choice[int] (active, pending, done)
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM notes WHERE number = ?", (note,))
        row = cur.fetchone()
        if not row:
            conn.close()
            await interaction.response.send_message(
                content=f"There's no note #{note}.",
                ephemeral=True
            )
            return
        if row[4] == notetype.name:
            conn.close()
            await interaction.response.send_message(
                content=f"Note #{note} is already set as {notetype.name}.",
                ephemeral=True
            )
        cur.execute("UPDATE notes SET active = ? WHERE number = ?", (notetype.name, note))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"Note #{note} has been set as {notetype.name}.", ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Notes(bot))
