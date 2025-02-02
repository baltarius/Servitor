# fightgame.py
"""
Small game of battles.

This cog is for the game of battles, which
includes the commands and the automatic database
for the battles and the scores ranking.

Author: Elcoyote Solitaire
"""
import discord

from discord import app_commands, Interaction
from discord.ext import commands
from discord.app_commands import Choice
from cogs.intercogs import get_server_database, add_achievement, add_achievecount, check_optin



class Fightgame(commands.Cog, name="fightgame"):
    """
    Class for the battles system.

    This class contains commands, automatic database
    and ranking stats for the battles' system.

    Functions:
        combat()
        user_fights()
        format_fights()
        

    Commands:
        /fight
        /battleboard
        /pending_fights
        /remove_fighter
    """
    def __init__(self, bot):
        self.bot = bot


    async def combat(
        self, guild_id, user_id, opponent_id, fattk1, fattk2, fattk3, fdef1, fdef2, fdef3
    ):
        """
        Combat function to allow points to the fighters
        
        Args:
            guild_id as interaction.guild.id
            fightchanname as get_channel(chan.id)
            user_id as interaction.user.id
            opponent_id as discord.Member.id
            attack1 as integer (1~3)
            attack2 as integer (1~3)
            attack3 as integer (1~3)
            defense1 as integer (1~3)
            defense2 as integer (1~3)
            defense3 as integer (1~3)
        Returns:
            fscore as integer
            oscore as integer
        """
        conn, cur = get_server_database(guild_id)

        cur.execute(
            "SELECT * FROM fightgame WHERE attackid = ? AND opponentid = ?",
            (opponent_id, user_id)
        )
        fightmoves = cur.fetchall()[0]
        fscore = 0
        oscore = 0
        oattk1 = fightmoves[2]
        oattk2 = fightmoves[3]
        oattk3 = fightmoves[4]
        odef1 = fightmoves[5]
        odef2 = fightmoves[6]
        odef3 = fightmoves[7]
        fattks = [fattk1.value, fattk2.value, fattk3.value]
        fdefs = [fdef1.value, fdef2.value, fdef3.value]
        oattks = [oattk1, oattk2, oattk3]
        odefs = [odef1, odef2, odef3]

        for fattk, odef in zip(fattks, odefs):
            if fattk != odef:
                fscore += 2
            else:
                oscore += 5

        for fdef, oattk in zip(fdefs, oattks):
            if fdef == oattk:
                fscore += 5
            else:
                oscore += 2
        cur.execute(
            "DELETE FROM fightgame WHERE attackid = ? AND opponentid = ?",
            (opponent_id, user_id)
        )
        conn.commit()
        cur.execute("SELECT score, games FROM fightscore WHERE id = ?", (user_id, ))
        fcombatscore = cur.fetchone()
        fgames = fcombatscore[1] + 1 if fcombatscore else 1
        if fcombatscore:
            fnewscore = fcombatscore[0] + fscore
            cur.execute(
                "UPDATE fightscore SET score = ?, games = ? WHERE id = ?",
                (fnewscore, fgames, user_id)
            )
            conn.commit()
        else:
            fnewscore = fscore
            cur.execute(
                "INSERT INTO fightscore (id, score, games) VALUES (?, ?, ?)",
                (user_id, fscore, fgames)
            )
            conn.commit()
        cur.execute("SELECT score, games FROM fightscore WHERE id = ?", (opponent_id, ))
        ocombatscore = cur.fetchone()
        ogames = ocombatscore[1] + 1 if ocombatscore else 1
        if ocombatscore:
            onewscore = ocombatscore[0] + oscore
            cur.execute(
                "UPDATE fightscore SET score = ?, games = ? WHERE id = ?",
                (onewscore, ogames, opponent_id)
            )
            conn.commit()
        else:
            cur.execute(
                "INSERT INTO fightscore (id, score, games) VALUES (?, ?, ?)",
                (opponent_id, oscore, ogames)
            )
            conn.commit()
        conn.close()
        return fscore, fnewscore, oscore


    @app_commands.command(
        name="fight",
        description="Attack another member"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(5, 1800.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(
        opponent="Your opponent",
        attack1="First attack",
        attack2="Second attack",
        attack3="Third attack",
        defense1="First defense",
        defense2="Second defense",
        defense3="Third defense"
    )
    @app_commands.choices(attack1=[
        Choice(name="upper attack", value=1),
        Choice(name="middle attack", value=2),
        Choice(name="lower attack", value=3)
    ])
    @app_commands.choices(attack2=[
        Choice(name="upper attack", value=1),
        Choice(name="middle attack", value=2),
        Choice(name="lower attack", value=3)
    ])
    @app_commands.choices(attack3=[
        Choice(name="upper attack", value=1),
        Choice(name="middle attack", value=2),
        Choice(name="lower attack", value=3)
    ])
    @app_commands.choices(defense1=[
        Choice(name="upper defense", value=1),
        Choice(name="middle defense", value=2),
        Choice(name="lower defense", value=3)
    ])
    @app_commands.choices(defense2=[
        Choice(name="upper defense", value=1),
        Choice(name="middle defense", value=2),
        Choice(name="lower defense", value=3)
    ])
    @app_commands.choices(defense3=[
        Choice(name="upper defense", value=1),
        Choice(name="middle defense", value=2),
        Choice(name="lower defense", value=3)
    ])
    async def fight(
        self, interaction: Interaction, opponent: discord.Member, attack1: Choice[int],
        attack2: Choice[int], attack3: Choice[int], defense1: Choice[int],
        defense2: Choice[int], defense3: Choice[int]
    ):
        """
        Main fight command.

        Allows a member to both attack and reply to an attack.
        The command verify if the member has alredy attacked the
        opponent, then verify if the opponent already attacked him.

        Args:
            interaction as discord.Interaction
            opponent as discord.Member
            attack1 as a choice
            attack2 as a choice
            attack3 as a choice
            defense1 as a choice
            defense2 as a choice
            defense3 as a choice
        """
        if opponent == interaction.user:
            await interaction.response.send_message(
                content = "You can't attack yourself!", ephemeral=True
            )
            return
        if opponent.bot:
            await interaction.response.send_message(
                content = "Please don't hurt our applications (bots)!", ephemeral=True
            )
            return
        user = interaction.user

        self_optin = await check_optin(interaction.guild.id, interaction.user.id, "fight")
        if self_optin == False:
            await interaction.response.send_message(
                content="You can't attack other members while opted out of the fight system.",
                ephemeral=True
            )
            return

        optin = await check_optin(interaction.guild.id, opponent.id, "fight")
        if optin == False:
            await interaction.response.send_message(
                content=f"{opponent.mention} has opted out of the fight system."
                "You can't attack that member.",
                ephemeral=True
            )
            return

        conn, cur = get_server_database(interaction.guild.id)

        cur.execute(
            "SELECT 1 FROM fightgame WHERE attackid = ? AND opponentid = ?",
            (user.id, opponent.id)
        )
        has_attacked = cur.fetchone()
        cur.execute(
            "SELECT * FROM fightgame WHERE attackid = ? AND opponentid = ?",
            (opponent.id, user.id)
        )
        is_replying = cur.fetchall()

        if has_attacked:
            await interaction.response.send_message(
                content="You already attacked that member. Please wait for a response.",
                ephemeral=True
            )
            conn.close()
            return

        cur.execute("SELECT id FROM setup WHERE chans = ?", ("fight",))
        row = cur.fetchone()
        if not row:
            await interaction.response.send_message(
                content="There is no fight channel set. Please contact an admin.",
                ephemeral=True
            )
            conn.close()
            return
        fightchanname = self.bot.get_channel(row[0])

        await add_achievement(interaction.guild.id, interaction.user.id, "Feisty")
        count = await add_achievecount(interaction.guild.id, interaction.user.id, "Belligerent")
        if count == 20:
            await add_achievement(interaction.guild.id, interaction.user.id, "Belligerent")

        if is_replying:
            conn.close()
            fscore, fnewscore, oscore = await self.combat(
                interaction.guild.id, user.id, opponent.id,
                attack1, attack2, attack3, defense1, defense2, defense3
            )
            await interaction.response.send_message(
                content=f"You made a score of {fscore}. You now have {fnewscore} points.",
                ephemeral=True
            )
            await fightchanname.send(
                f"The fight is over. {user.mention}: {fscore} - {opponent.mention}: {oscore}"
            )
            return

        cur.execute(
            "INSERT INTO fightgame (attackid, opponentid, attack1, attack2, attack3, "
            "defense1, defense2, defense3) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user.id, opponent.id, attack1.value, attack2.value, attack3.value,
                defense1.value, defense2.value, defense3.value
            )
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"You just attacked {opponent.mention}! Wait for the response.",
            ephemeral=True
        )
        await fightchanname.send(
            content=f"{user.mention} just attacked {opponent.mention}. Defend yourself! Use /fight"
        )


    @app_commands.command(
        name="battleboard",
        description="Battleboard for fight game scores"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def battleboard(self, interaction: Interaction):
        """
        Battleboard for fight game scores.

        Display the battleboard of the server for
        the top 10 of the fight game system.

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
        conn, cur = get_server_database(interaction.guild.id)

        cur.execute("SELECT * FROM fightscore")
        top_scores = cur.fetchall()
        conn.close()

        if not top_scores:
            await interaction.response.send_message(
                content="There is no score yet on this server for the fight system.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title=f"Battleboard of {interaction.guild.name}", color=0x00ff00)
        embed.set_thumbnail(url=interaction.guild.icon)

        sorted_points = sorted(top_scores, key=lambda x: (-x[1], -x[2]))[:10]
        boardpoints = ""
        for item in sorted_points:
            member = self.bot.get_user(int(item[0]))
            if member is not None:
                member = member.display_name
            else:
                member = f"<@{item[0]}>"
            boardpoints += f"{member}: {item[1]} points\n"

        sorted_games = sorted(top_scores, key=lambda x: (-x[2], -x[1]))[:10]
        boardgames = ""
        for item in sorted_games:
            member = self.bot.get_user(int(item[0]))
            if member is not None:
                member = member.display_name
            else:
                member = f"<@{item[0]}>"
            boardgames += f"{member}: {item[2]} games\n"

        embed.add_field(name="Top 10 scores", value=boardpoints, inline=True)
        embed.add_field(name="Top 10 games", value=boardgames, inline=True)
        await interaction.response.send_message(embed=embed)


    async def user_fights(self, guild_id, user_id):
        """
        Function to find pending fights of a member

        Checks if the member as fight as both attacker and
        opponent to return a list of the pending fights.

        Args:
            guild_id as interaction.guild.id
            user_id as discord.User.id

        return:
            attkvsfoe
            foevsattk
        """
        conn, cur = get_server_database(guild_id)
        cur.execute("SELECT attackid, opponentid FROM fightgame")
        rows = cur.fetchall()
        conn.close()

        member = self.bot.get_user(user_id)
        user_vs_opponent = []
        opponent_vs_user = []
        attkvsfoe = ""
        foevsattk = ""

        for row in rows:
            attackid, opponentid = row

            if attackid == user_id:
                user_vs_opponent.append((user_id, opponentid))

            elif opponentid == user_id:
                opponent_vs_user.append((attackid, user_id))

        if user_vs_opponent:
            for item in user_vs_opponent:
                opponent = self.bot.get_user(item[1])
                opponent_name = opponent.display_name if opponent else f"<@{item[1]}>"
                attkvsfoe += f"{member.display_name} // {opponent_name}\n"

        if opponent_vs_user:
            for item in opponent_vs_user:
                attacker = self.bot.get_user(item[0])
                attacker_name = attacker.display_name if attacker else f"<@{item[0]}>"
                foevsattk += f"{attacker_name} // {member.display_name}\n"

        return attkvsfoe, foevsattk


    async def format_fights(self, fights, sort_index, field_name):
        """
        Function to format fights sorted by attacker and by opponent

        Args:
            fights as a list of rows
            sort_index as an integer (0/1)
            field_name as a str for the field name

        Return:
            field_name
            attkvsfoe
        """
        sorted_fights = sorted(fights, key=lambda x: x[sort_index])
        attkvsfoe = ""

        for item in sorted_fights:
            attacker = self.bot.get_user(item[0])
            attacker_name = attacker.display_name if attacker else f"<@{item[0]}>"
            opponent = self.bot.get_user(item[1])
            opponent_name = opponent.display_name if opponent else f"<@{item[1]}>"
            attkvsfoe += f"{attacker_name} // {opponent_name}\n"

        return (field_name, attkvsfoe)


    @app_commands.command(
        name="pending_fights",
        description="Shows all pending fights"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        allmembers="Choose between all members or one fighter/opponent",
        member="Enter a member to see their pending fights or skip to see yours"
    )
    @app_commands.choices(allmembers=[
        Choice(name="all", value=1),
        Choice(name="member's fights", value=2)
    ])
    async def pending_fights(
        self, interaction: Interaction, allmembers: Choice[int], member: discord.User = None
    ):
        """
        Shows all pending fights in the database.

        Calls:
            self.format_fights
            self.user_fights

        Args:
            interaction as discord.Interaction
        """
        member = member or interaction.user
        if allmembers.name == "all":
            if not interaction.user.guild_permissions.administrator:
                await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
                await interaction.response.send_message(
                    content="Only admins can see all the fights",
                    ephemeral=True
                )
                return
            permissions = interaction.channel.permissions_for(interaction.channel.guild.me)
            if not permissions.embed_links:
                await interaction.response.send_message(
                    content="I don't have the permissions to send embed in "
                    f"{interaction.channel.mention}",
                    ephemeral=True
                )
                return
            conn, cur = get_server_database(interaction.guild.id)

            cur.execute("SELECT attackid, opponentid FROM fightgame ORDER BY attackid ASC")
            fights = cur.fetchall()
            conn.close()

            if not fights:
                await interaction.response.send_message(
                    content="There is no pending fight on the server.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"Pendings fights in {interaction.guild.name}", color=0xb80f0a
            )
            embed.set_thumbnail(url=interaction.guild.icon)

            field_name, attkvsfoe = (
                await self.format_fights(fights, 0, "Attacker vs opponent\nSorted by attacker")
            )
            embed.add_field(name=field_name, value=attkvsfoe, inline=False)

            field_name, oppvsattk = (
                await self.format_fights(fights, 1, "Attacker vs opponent\nSorted by opponent")
            )
            embed.add_field(name=field_name, value=oppvsattk, inline=False)

            embed.add_field(
                name="", value="All opponents are requested to fight back with /fight",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        else:
            if ( member.id != interaction.user.id
                and not interaction.user.guild_permissions.administrator
            ):
                await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
                await interaction.response.send_message(
                    content="You are not allowed to check other's pending fights.",
                    ephemeral=True
                )
                return

            attkvsfoe, foevsattk = await self.user_fights(interaction.guild.id, member.id)

            if not attkvsfoe and not foevsattk:
                await interaction.response.send_message(
                    content=f"{member.display_name} has no pending fights on the server.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"Pending fights for {member.display_name}", color=0xb80f0a
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(
                name=f"{member.display_name} vs opponents",
                value=attkvsfoe,
                inline=True
            )
            embed.add_field(
                name=f"Attackers vs {member.display_name}",
                value=foevsattk,
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(
        name="remove_fighter",
        description="Deletes battles of a member from the table"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Enter the member to be removed from the fights table")
    async def remove_fighter(self, interaction: Interaction, member: discord.User):
        """
        Removes a fighter from the fights table

        Args:
            member as discord.User which accepts user ID.
        """
        user_id = member.id
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "DELETE FROM fightgame WHERE attackid = ? OR opponentid = ?", (user_id, user_id)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"{member} has been removed from the fights table.",
            ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Fightgame(bot))
