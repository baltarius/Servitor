# voice.py
"""
Voice logs system cog.

This cog is for logging and compiling different
informations about the voice activities.

This system includes logging members joining,
switching and leaving voice channels. It also
compile the time spent on voice for each of
the members of the server.

Author: Elcoyote Solitaire
"""
import datetime
import discord

from datetime import datetime
from discord.ext import commands
from discord.utils import get
from cogs.intercogs import get_server_database, add_achievement, add_achievecount



class Voice(commands.Cog, name="voice"):
    """
    Voice class for server logs and infos.

    This class contains listeners to log and compile voice activities.

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot


    async def voice_stats(self, server_id, member_id, minutes):
        """
        Updates member's stats for voice activity.

        See on_voice_state_update()

        Args:
            server_id as member.guild.id
            member_id as member.id (int)
            minutes as an integer
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT tvoice, jvoice FROM stats WHERE id = ?", (member_id,))
        row = cur.fetchone()
        if row:
            minutes_total = minutes + row[0] if row[0] is not None else minutes
            voice_total = 1 + row[1] if row[1] is not None else 1
            cur.execute("UPDATE stats SET tvoice = ?, jvoice = ? WHERE id = ?",
                (minutes_total, voice_total, member_id)
            )
            conn.commit()

        else:
            cur.execute(
                "INSERT INTO stats (id, tvoice, jvoice) VALUES(?, ?, ?)",
                (member_id, minutes, 1)
            )
            conn.commit()
        conn.close()


    async def voice_entry(self, server_id, member_id, embmsg_id: int):
        """
        Updates member's entry (timestamp) for voice activity.

        See on_voice_state_update()

        Args:
            server_id as member.guild.id
            member_id as member.id (int)
        """
        conn, cur = get_server_database(server_id)
        cur.execute(
            "INSERT OR REPLACE INTO voice (id, jtime, embmsg) VALUES (?, ?, ?)",
            (member_id, datetime.now(), embmsg_id)
        )
        conn.commit()
        conn.close()


    async def getemb(self, server_id, member_id):
        """
        Retrieves embed message for member.

        See on_voice_state_update()

        Args:
            server_id as member.guild.id
            member_id as member.id (int)
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT embmsg FROM voice WHERE id = ?", (member_id,))
        row = cur.fetchone()
        embmsg = row[0] if row else False
        conn.close()
        return embmsg


    async def entry_calc(self, server_id, member_id):
        """
        Calculates member's minutes in voice and clears entry.

        Takes the entry (timestamp) in the voice table for the
        member and calculates the datetime.now minus entry then
        returns the minutes.
        Clears the entry in the table for the member.

        See on_voice_state_update()

        Args:
            server_id as member.guild.id
            member_id as member.id (int)
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT jtime FROM voice WHERE id = ?", (member_id,))
        row = cur.fetchone()
        db_timestamp = datetime.fromisoformat(row[0])
        stamp_calc = datetime.now() - db_timestamp
        minutes = round(stamp_calc.total_seconds() / 60)
        cur.execute("DELETE FROM voice WHERE id = ?", (member_id,))
        conn.commit()
        conn.close()
        return minutes


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Listener to voice channel updates.

        Listening to any voice channel updates, this will
        log informations about who joins/switches/leaves
        voice channel, but also compile informations per
        members on the server.

        Args:
            member as discord.Member
            before
            after
        """
        if member.bot:
            return
        server_id = member.guild.id
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("voices",))
        result = cur.fetchone()
        conn.close()
        chanlog = self.bot.get_channel(result[0])
        if chanlog:
            permissions = chanlog.permissions_for(chanlog.guild.me)

        if before.channel is None and after.channel is not None:
            if permissions.embed_links:
                embed = discord.Embed(
                    color=0xFFFFFF,
                    title="",
                    description=""
                )
                embed.add_field(
                    name="Voice activity",
                    value=f"{datetime.now().strftime('%H:%M:%S')}: "
                    f"{member.mention} joined {after.channel.mention}.",
                    inline=False
                )
                embmsg = await chanlog.send(embed=embed)
            if embmsg:
                await self.voice_entry(server_id, member.id, embmsg.id)
            else:
                await self.voice_entry(server_id, member.id, "None")
            await add_achievement(server_id, member.id, "Vocal")
            count = await add_achievecount(message.guild.id, message.author.id, "Garrulous")
            if count == 20:
                await add_achievement(message.guild.id, message.author.id, "Garrulous")

        elif before.channel is not None and after.channel is not None:
            if before.channel != after.channel:
                embmsg = await self.getemb(server_id, member.id)
                if embmsg:
                    embedmsg = await chanlog.fetch_message(embmsg)
                    embed = embedmsg.embeds[0]
                    activity = embed.fields[0].value
                    activity += (
                        f"\n{datetime.now().strftime('%H:%M:%S')}: {member.display_name} "
                        f"switched from {before.channel.mention} to {after.channel.mention}"
                    )
                    embed.set_field_at(0, name="Voice activity", value=activity)
                    await embedmsg.edit(embed=embed)

        elif before.channel is not None and after.channel is None:
            embmsg = await self.getemb(server_id, member.id)
            minutes = await self.entry_calc(server_id, member.id)
            if embmsg:
                embedmsg = await chanlog.fetch_message(embmsg)
                embed = embedmsg.embeds[0]
                activity = embed.fields[0].value
                activity += (
                    f"\n{datetime.now().strftime('%H:%M:%S')}: {member.display_name} "
                    f"left {before.channel.mention}"
                )
                embed.set_field_at(0, name="Voice activity", value=activity)
                embed.set_footer(
                    text=f"Lasted: {minutes} minutes."
                )
                await embedmsg.edit(embed=embed)
            await self.voice_stats(server_id, member.id, minutes)



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Voice(bot))
