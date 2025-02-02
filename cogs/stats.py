# stats.py
"""
User statistics cog.

This cog is for user statistics (gather, process and display).
The stats include msgs, words, characters and emojis but also
reactions, messages edited/deleted and time spent in voice. 

Author: Elcoyote Solitaire
"""
import random
import math
import discord
import emoji

from discord import app_commands, Interaction
from discord.ext import commands
from discord.ext.commands import Context
from discord.app_commands import Choice, context_menu
from discord.utils import get
from cogs.intercogs import get_server_database, is_exception, add_achievement, get_achievements



class Stats(commands.Cog, name="stats"):
    """
    Statistics class for users.

    This class contains listeners and commands used for the stats system.

    Functions:
        update_stats()
        update_level()
        top_stats()
        generate_stats()
        generate_stats2()
        generate_card()

    Commands:
        /setrole
        /stats
        /stats2
        /leaderboard
        /level
        /reset
        /addexp
        /levelboard
    CTX commands:
        level
        stats
        stats2
        profile
    """
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.context_menu(name="profile")(self.check_profile)
        self.bot.tree.context_menu(name="stats")(self.check_stats)
        self.bot.tree.context_menu(name="level")(self.check_level)
        self.bot.tree.context_menu(name="stats2")(self.check_stats2)
        self.bot.tree.context_menu(name="all-stats")(self.all_stats)


    async def update_stats(
        self, user_id, msg, mots, chars, emos, react, edits, deletes, server_id
    ):
        """
        Updates the stats of the user.

        Args:
            id as user.id
            msg as integer - The amount of messages.
            mots as integer - The amount of words.
            chars as integer - The amount of characters.
            emos as integer - The amount of emojis
            react as integer - The amount of reactions
            edits as integer - The amount of messages edited.
            deletes as integer - The amount of messages deleted.
            server_id as guild.id
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT * FROM stats WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            messages = row[1] + msg if row[1] is not None else msg
            words = row[2] + mots if row[2] is not None else mots
            characters = row[3] + chars if row[3] is not None else chars
            emojis = row[4] + emos if row[4] is not None else emos
            reactions = row[5] + react if row[5] is not None else react
            edited = row[6] + edits if row[6] is not None else edits
            deleted = row[7] + deletes if row[7] is not None else deletes

            cur.execute(
                "UPDATE stats SET messages = ?, words = ?, characters = ?, emojis = ?, "
                "reactions = ?, edited = ?, deleted = ? WHERE id = ?", 
                (messages, words, characters, emojis, reactions, edited, deleted, user_id)
            )
            conn.commit()
            conn.close()

        else:
            cur.execute(
                "INSERT INTO stats (id, messages, words, characters, emojis, "
                "reactions, edited, deleted) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, msg, mots, chars, emos, react, edits, deletes)
            )
            conn.commit()
            conn.close()


    async def update_level(self, context, user_id, exp, server_id):
        """
        Updates the level of the user.

        Args:
            id: the ID of the user.
            exp: the amount of exp to add.
            server_id: The ID of the server.
        """
        conn, cur = get_server_database(server_id)
        cur.execute("SELECT * FROM level WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            # user exists already, update the stats.
            total = row[3] + exp
            exp = row[1] + exp
            level = row[2]
            if exp / 1000 > 1:
                exp -= 1000
                level += 1
                cur.execute(
                    "UPDATE level SET exp = ?, level = ?, total = ? WHERE id = ?",
                    (exp, level, total, user_id)
                )
                conn.commit()
                cur.execute("SELECT id FROM setup WHERE chans = ?", ("level",))
                result = cur.fetchone()
                member = f"<@{user_id}>"
                lvlup_msg = [
                    f"Congratulations {member} for reaching level {level}!",
                    f"{member} is on fire! and also now level {level}.",
                    f"I can't believe it! {member} made it to level {level}!",
                    f"DING DING DING! {member} just reached level {level}!",
                    f"Snap! Member: {member} - level: {level}"
                ]
                if not result:
                    conn.close()
                    return
                levelchanname = self.bot.get_channel(int(result[0]))
                permissions = levelchanname.permissions_for(context.guild.me)
                if permissions.send_messages:
                    await levelchanname.send(random.choice(lvlup_msg))
                if level % 10 == 0:
                    lvlreward = f"Level {level}"
                    cur.execute("SELECT id FROM setup WHERE chans = ?", (lvlreward,))
                    result = cur.fetchone()
                    if result:
                        reward_role = context.guild.get_role(result[0])
                        member_reward = context.guild.get_member(user_id)
                        await member_reward.add_roles(reward_role)

                conn.close()

            else:
                cur.execute(
                    "UPDATE level SET exp = ?, total = ? WHERE id = ?", (exp, total, user_id)
                )
                conn.commit()
                conn.close()

        else:
            cur.execute(
                "INSERT INTO level (id, exp, level, total) VALUES(?, ?, ?, ?)",
                (user_id, exp, 0, exp)
            )
            conn.commit()
            conn.close()


    @app_commands.command(
        name="setrole",
        description="Setups roles for level system"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        lvl="Choose the level",
        lvlrole="Choose the role"
    )
    @app_commands.choices(lvl=[
        Choice(name="Level 10", value=1),
        Choice(name="Level 20", value=2),
        Choice(name="Level 30", value=3),
        Choice(name="Level 40", value=4),
        Choice(name="Level 50", value=5),
        Choice(name="Level 60", value=6),
        Choice(name="Level 70", value=7),
        Choice(name="Level 80", value=8),
        Choice(name="Level 90", value=9),
        Choice(name="Level 100", value=10)
    ])
    async def setrole(
        self, interaction: Interaction, lvl: Choice[int], lvlrole: discord.Role
    ):
        """
        Roles for leveling up.

        This command is used to select which role
        goes for every 10 level ups.

        Args:
            interaction as discord.Interaction.
            lvl as a choice for every 10 levels.
            lvlrole as a Role from the server.
        """
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "INSERT OR REPLACE INTO setup (chans, id) VALUES (?, ?)", (lvl.name, lvlrole.id)
        )
        conn.commit()
        await interaction.response.send_message(
            content=f"{lvlrole.mention} has been set as {lvl.name}'s reward.",
            ephemeral=True
        )
        conn.close()


    @app_commands.command(
        name="stats",
        description="Displays the user's stats"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(5, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(user="Optionnal to see a user stats")
    async def stats(self, interaction: Interaction, user: discord.User = None):
        """
        Stats command that displays the stats of a member.
        Can be used with or without a discord member.

        Args:
            interaction as discord.Interaction
            user as discord.Member (None by default)
        """
        user = user or interaction.user
        if user.bot:
            await interaction.response.send_message(
                content="Bots don't have stats.",
                ephemeral=True
            )
            return
        if user not in interaction.guild.members:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content=f"{user} is not a member of {interaction.guild.name}.",
                ephemeral=True
            )
            return

        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM stats WHERE id = ?", (user.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            await interaction.response.send_message("This user has no stats yet.", ephemeral=True)
        else:
            embed = discord.Embed(title=f"{user.display_name}'s stats", color=0x00ff00)
            embed.set_thumbnail(url=user.avatar)
            embed.add_field(name="Messages sent", value=result[1], inline=True)
            embed.add_field(name="Words written", value=result[2], inline=True)
            embed.add_field(name="Characters written", value=result[3], inline=True)
            embed.add_field(name="Emojis used", value=result[4], inline=True)
            embed.add_field(name="Reactions", value=result[5], inline=True)
            embed.add_field(name="Messages edited", value=result[6], inline=True)
            embed.add_field(name="Messages deleted", value=result[7], inline=True)
            if result[8]:
                embed.add_field(name="Voice sessions:", value=result[8], inline=True)
                embed.add_field(name="Voice time:", value=f"{result[9]} minutes", inline=True)
            embed.add_field(name="User:", value=user, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await add_achievement(interaction.guild.id, user.id, "Statistics")


    @app_commands.command(
        name="leaderboard",
        description="Displays de Leaderboard for stats"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def leaderboard(self, interaction: Interaction):
        """
        Leaderboard for stats.

        Display the leaderboard of the server for
        each category of the stats system.

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
        guild = interaction.guild
        conn, cur = get_server_database(guild.id)

        highest_stats = {}
        highest_stats_processed = {}
        stat_name_mapping = {
            'messages': 'Messages sent',
            'words': 'Words written',
            'characters': 'Characters written',
            'emojis': 'Emojis used',
            'reactions': 'Reactions',
            'edited': 'Messages edited',
            'deleted': 'Messages deleted',
            'jvoice': 'Voice sessions',
            'tvoice': 'Voice time',
        }
        columns = [
            "messages", "words", "characters", "emojis", "reactions",
            "edited", "deleted", "jvoice", "tvoice"
        ]
        for column in columns:
            cur.execute(f"SELECT id, MAX({column}) FROM stats")
            result = cur.fetchone()
            highest_stats[column] = result
        conn.close()

        for column, (user_id, stats_value) in highest_stats.items():
            member = self.bot.get_user(user_id)
            if member is not None:
                member_name = member.display_name
            else:
                member_name = f"<@{user_id}>"
            if stats_value is not None and stats_value != 0:
                highest_stats_processed[column.lower()] = f"{member_name} - {stats_value}"
            else:
                if column == "jvoice" or column == "tvoice":
                    highest_stats_processed[column.lower()] = f"No vocal yet"
                else:
                    highest_stats_processed[column.lower()] = f"No {column} yet"

        embed = discord.Embed(title=f"Leaderboard of {guild.name}", color=0x00ff00)
        embed.set_thumbnail(url=guild.icon)
        for stat_name, value in highest_stats_processed.items():
            friendly_name = stat_name_mapping.get(
                stat_name, stat_name.replace("_", " ").capitalize()
            )
            embed.add_field(name=friendly_name, value=value, inline=False)

        await interaction.response.send_message(embed=embed)
        conn.close()


    @app_commands.command(
        name="level",
        description="Displays the user's level"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(5, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(user="Optionnal to see a user level")
    async def level(self, interaction: Interaction, user: discord.User = None):
        """
        Level command that displays the level of a member.
        Can be used with or without a discord member.

        Args:
            interaction as discord.Interaction
            user as discord.Member (None by default)
        """
        user = user or interaction.user
        if user.bot:
            await interaction.response.send_message(
                content="Bots can't have exp.",
                ephemeral=True
            )
            return
        if user not in interaction.guild.members:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content=f"{user} is not a member of {interaction.guild.name}.",
                ephemeral=True
            )
            return

        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM level WHERE id = ?", (user.id,))
        result = cur.fetchone()

        if result is None:
            await interaction.response.send_message("This user has no exp yet.", ephemeral=True)
            conn.close()
        else:
            level = result[2]
            exp = result[1]
            pcent_exp = round(exp / 10, 2)
            total = result[3]
            target_data = total

            cur.execute("SELECT total, RANK() OVER (ORDER BY total DESC) AS rank FROM level")
            rows = cur.fetchall()

            rank = next((row[1] for row in rows if row[0] == target_data), None)

            cur.execute("SELECT COUNT(*) FROM level")
            row_count = cur.fetchone()[0]
            conn.close()

            embed = discord.Embed(title=f"{user.display_name}'s level", color=0x0000FF)
            embed.set_thumbnail(url=user.avatar)
            embed.add_field(name="Level:", value=level, inline=True)
            embed.add_field(name="Exp:", value=f"{pcent_exp}%", inline=True)
            embed.add_field(name="Rank:", value=f"#{rank}/{row_count}", inline=True)
            embed.add_field(name="User:", value=user, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
            await add_achievement(interaction.guild.id, user.id, "Level")


    @app_commands.command(
        name="levelboard",
        description="Displays the Leaderboard for levels"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def levelboard(self, interaction: Interaction):
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
        guild = interaction.guild
        conn, cur = get_server_database(guild.id)

        cur.execute("SELECT id, level, exp FROM level ORDER BY total DESC LIMIT 10")
        top_levels = cur.fetchall()
        conn.close()

        embed = discord.Embed(title=f"Levelboard of {guild.name}", color=0x00ff00)
        top_level_info = []
        embed.set_thumbnail(url=guild.icon)
        for rank, (user_id, level, exp) in enumerate(top_levels, start=1):
            member = self.bot.get_user(user_id)
            exp_percentage = round(exp / 10, 2)
            if member is not None:
                member = member.display_name
                top_level_info.append(f"{rank}: {member} - Level {level} ({exp_percentage}%)")
            else:
                member = f"<@{user_id}>"
                top_level_info.append(f"{rank}: {member} - Level {level} ({exp_percentage}%)")
            embed.add_field(
                name=f"{rank}: {member} - Lvl {level} ({exp_percentage}%)",
                value="",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="reset_lvl",
        description="Resets a user's level"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The user to whom you wish to reset the level")
    async def reset_lvl(self, interaction: Interaction, user: discord.Member = None):
        """
        Reset command that reset the level of a member.
        Can be used with or without a discord member.

        Args:
            interaction as discord.Interaction
            user as discord.Member (None by default)
        """
        user = user or interaction.user
        if user.bot:
            await interaction.response.send_message(
                content="Bots don't have experience.",
                ephemeral=True
            )
            return
        conn, cur = get_server_database(interaction.guild.id)

        cur.execute(
            "UPDATE level SET exp = ?, level = ?, total = ? WHERE id = ?", (0, 0, 0, user.id)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"{user}'s experience has been reset to 0.",
            ephemeral=True
        )


    @app_commands.command(
        name="addexp",
        description="Adds experience to a user"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        user="The user to whom the experience goes",
        exp="The amount of exp to give (1~1000)"
    )
    async def addexp(self, interaction: Interaction, user: discord.Member, exp: int):
        """
        Command that adds an amount of experience to a member (max 1000).

        Args:
            interaction as discord.Interaction
            user as discord.Member
            exp: the amount of exp to add (from 1 to 1000).
        """
        if user.bot:
            await interaction.response.send_message(
                content="Applications don't participate in exp system.",
                ephemeral=True
            )
            return
        if 1 <= exp <= 1000:
            await self.update_level(interaction, user.id, exp, interaction.guild.id)
            await interaction.response.send_message(
                content=f"Added {exp} experience to {user}.",
                ephemeral=True
            )
        else:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                f"{exp} is out of range. Must be from 1 to 1000.",
                ephemeral=True
            )


    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listener for messages.

        Args:
            message: The message.
        """
        if str(message.channel.type) == "private":
            return
        if message.author.bot:
            return
        if is_exception(message.guild.id, message.channel.id, "exp"):
            return

        server_id = message.guild.id
        user_id = message.author.id
        context = await self.bot.get_context(message)
        words = message.content.split()
        nbr_words = len(words)
        characters = 0
        emojis = 0
        for char in message.content:
            if emoji.is_emoji(char) is True:
                emojis += 1
        characters = len(''.join(words))
        characters -= emojis
        nbr_words -= emojis
        get_server_database(server_id)
        await self.update_stats(
            user_id, 1, nbr_words, characters, emojis, 0, 0, 0, server_id
        )
        exp = math.ceil(characters/10 + random.randint(3,5))
        await self.update_level(context, user_id, exp, server_id)


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """
        Listener for message deletion.

        Args:
            message: The deleted message.
        """
        if str(message.channel.type) == "private":
            return
        if message.author.bot:
            return
        await self.update_stats(
            message.author.id, 0, 0, 0, 0, 0, 0, 1, message.guild.id
        )


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        Listener for reactions.

        Args:
            reaction: The reaction.
            user: The user doing the reaction.
        """
        if str(reaction.message.channel.type) == "private":
            return
        if user.bot:
            return
        await self.update_stats(
            user.id, 0, 0, 0, 0, 1, 0, 0, reaction.message.guild.id
        )


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """
        Listener for edited messages.
        
        Args:
            before: The message before the edition.
            after: The message after the edition.
        """
        if str(after.channel.type) == "private":
            return
        if after.author.bot:
            return
        if before.author.bot:
            return

        await self.update_stats(after.author.id, 0, 0, 0, 0, 0, 1, 0, after.guild.id)


    @app_commands.command(
        name="stats2",
        description="user stats average"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(5, 60.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(user="Optionnal to see a user stats2")
    async def stats2(self, interaction: Interaction, user: discord.User = None):
        """
        Stats command that displays the stats average of a member.
        Can be used with or without a discord member.

        Args:
            interaction as discord.Interaction
            user as discord.Member (None by default)
        """
        user = user or interaction.user
        if user.bot:
            await interaction.response.send_message(
                content="Bots don't have stats.",
                ephemeral=True
            )
            return
        if user not in interaction.guild.members:
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                content=f"{user} is not a member of {interaction.guild.name}.",
                ephemeral=True
            )
            return

        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("SELECT * FROM stats WHERE id = ?", (user.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            await interaction.response.send_message("This user has no stats yet.", ephemeral=True)
        else:
            word_message = round(result[2] / result[1], 2)
            characters_message = round(result[3] / result[1], 2)
            emojis_message = round(result[4] / result[1], 2)
            characters_word = round(result[3] / result[2], 2)
            edited_message = round(result[6] / result[1] * 100, 2)
            deleted_message = round(result[7] / result[1] * 100, 2)

            embed = discord.Embed(title=f"{user.display_name}'s stats", color=0x00ff00)
            embed.set_thumbnail(url=user.avatar)
            embed.add_field(name="Words per message", value=word_message, inline=True)
            embed.add_field(name="Characters per message", value=characters_message, inline=True)
            embed.add_field(name="Characters per words", value=characters_word, inline=True)
            embed.add_field(name="Emojis per message", value=emojis_message, inline=True)
            embed.add_field(name="Ratio edited/message", value=f"{edited_message}%", inline=True)
            embed.add_field(name="Ratio deleted/message", value=f"{deleted_message}%", inline=True)
            if result[8]:
                minutes_join = round(result[9] / result[8], 2)
                embed.add_field(name="Minutes per voice session", value=minutes_join, inline=True)
            embed.add_field(name="User:", value=user, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await add_achievement(interaction.guild.id, user.id, "Statistics 2")


    async def top_stats(self, server_id, user_id):
        """
        Function to get the top stats.

        See the interaction menu function check_profile()

        Args:
            server_id as interaction.guild.id
            user_id as member.id.
        """
        conn, cur = get_server_database(server_id)

        highest_stats = {}
        member_top_stats = ""
        columns = [
            "messages", "words", "characters", "emojis", "reactions",
            "edited", "deleted", "jvoice", "tvoice"
        ]
        for column in columns:
            cur.execute(f"SELECT id, MAX({column}) FROM stats")
            result = cur.fetchone()
            if column == "tvoice":
                column_name = "Voice time"
            elif column == "jvoice":
                column_name = "Voice sessions"
            else:
                column_name = column
            highest_stats[column_name] = result
        conn.close()

        for column, (stats_id, stats_value) in highest_stats.items():
            #member = self.bot.get_user(user_id)
            #variable_name = column.lower()
            if user_id == stats_id:
                if column == "Voice time":
                    member_top_stats += f"Top {column} with {stats_value} minutes\n"
                else:
                    member_top_stats += f"Top {column} with {stats_value}\n"
        return member_top_stats


    async def check_profile(self, interaction: discord.Interaction, member: discord.Member):
        """
        interaction menu function for member's profile.

        Requires: self.top_stats()

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        conn, cur = get_server_database(interaction.guild.id)

        embed = discord.Embed(
            title=f"{member}'s Profile",
            description=f"{member.mention} ({member.id})",
            color=0x808080
        )

        cur.execute("SELECT * FROM level WHERE id = ?", (member.id,))
        levels = cur.fetchone()

        level = levels[2] if levels else 0
        exp = levels[1] if levels else 0
        pcent_exp = round(exp / 10, 2) if levels else 0
        total = levels[3] if levels else 0

        _, liste_1, liste_2, total_achieves = (
            await get_achievements(interaction.guild.id, member.id)
        )
        member_top_stats = await self.top_stats(interaction.guild.id, member.id)
        member_top_stats = member_top_stats if member_top_stats else "None"
        member_top_role = (
            member.top_role.mention if member.top_role.id != interaction.guild.id else "None"
        )
        if total_achieves - 10 <= 0:
            total_achieves_1 = total_achieves
        else:
            total_achieves_1 = 10
            total_achieves_2 = total_achieves % 10
        cur.execute("SELECT total, RANK() OVER (ORDER BY total DESC) AS rank FROM level")
        ranks = cur.fetchall()
        if ranks:
            rank = next((row[1] for row in ranks if row[0] == total), 0)
            cur.execute("SELECT COUNT(*) FROM level")
            member_rank = f"{rank}/{cur.fetchone()[0]}"
        else:
            member_rank = "N/A"
        cur.execute("SELECT * FROM fightscore WHERE id = ?", (member.id,))
        fightstats = cur.fetchone()
        if fightstats:
            points = fightstats[1] if fightstats[1] else 0
            matches = fightstats[2] if fightstats[2] else 0
        else:
            points = 0
            matches = 0
        conn.close()
        embed.add_field(
            name="Level / Rank",
            value=f"Level: {level} ({pcent_exp}%)\nRank: {member_rank}",
            inline=True
        )
        embed.add_field(
            name="Fight stats",
            value=f"Duels: {matches}\nScore: {points}",
            inline=True
        )
        embed.add_field(
            name="Top Role",
            value=member_top_role,
            inline=True
        )
        embed.add_field(
            name="Top stats",
            value=member_top_stats,
            inline=True
        )
        embed.add_field(
            name=f"Achievements ({total_achieves_1})",
            value=liste_1,
            inline=True
        )
        if liste_2:
            embed.add_field(
                name=f"Achievements ({total_achieves_2})",
                value=liste_2,
                inline=True
            )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await add_achievement(interaction.guild.id, interaction.user.id, "Profile")
        await add_achievement(interaction.guild.id, interaction.user.id, "Application")


    async def check_stats(self, interaction: discord.Interaction, member: discord.Member):
        """
        interaction menu function for member's stats.

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        conn, cur = get_server_database(interaction.guild.id)

        cur.execute("SELECT * FROM stats WHERE id = ?", (member.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            await interaction.response.send_message(
                content="This user has no stats yet.",
                ephemeral=True
            )
        else:
            embed = discord.Embed(title=f"{member.display_name}'s stats", color=0x00ff00)
            embed.set_thumbnail(url=member.avatar)
            embed.add_field(name="Messages sent", value=result[1], inline=True)
            embed.add_field(name="Words written", value=result[2], inline=True)
            embed.add_field(name="Characters written", value=result[3], inline=True)
            embed.add_field(name="Emojis used", value=result[4], inline=True)
            embed.add_field(name="Reactions", value=result[5], inline=True)
            embed.add_field(name="Messages edited", value=result[6], inline=True)
            embed.add_field(name="Messages deleted", value=result[7], inline=True)
            if result[8]:
                embed.add_field(name="Voice sessions:", value=result[8], inline=True)
                embed.add_field(name="Voice time:", value=f"{result[9]} minutes", inline=True)
            embed.add_field(name="User:", value=member, inline=False)
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        await add_achievement(interaction.guild.id, interaction.user.id, "Statistics")
        await add_achievement(interaction.guild.id, interaction.user.id, "Application")


    async def check_stats2(self, interaction: discord.Interaction, member: discord.Member):
        """
        interaction menu function for member's average stats.

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        conn, cur = get_server_database(interaction.guild.id)

        cur.execute("SELECT * FROM stats WHERE id = ?", (member.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            await interaction.response.send_message(
                content="This user has no stats yet.",
                ephemeral=True
            )
        else:
            word_message = round(result[2] / result[1], 2)
            characters_message = round(result[3] / result[1], 2)
            emojis_message = round(result[4] / result[1], 2)
            characters_word = round(result[3] / result[2], 2)
            edited_message = round(result[6] / result[1] * 100, 2)
            deleted_message = round(result[7] / result[1] * 100, 2)

            embed = discord.Embed(title=f"{member.display_name}'s stats", color=0x00ff00)
            embed.set_thumbnail(url=member.avatar)
            embed.add_field(name="Words per message", value=word_message, inline=True)
            embed.add_field(name="Characters per message", value=characters_message, inline=True)
            embed.add_field(name="Characters per words", value=characters_word, inline=True)
            embed.add_field(name="Emojis per message", value=emojis_message, inline=True)
            embed.add_field(name="Ratio edited/message", value=f"{edited_message}%", inline=True)
            embed.add_field(name="Ratio deleted/message", value=f"{deleted_message}%", inline=True)
            if result[8]:
                minutes_join = round(result[9] / result[8], 2)
                embed.add_field(name="Minutes per voice session", value=minutes_join, inline=True)
            embed.add_field(name="User:", value=member, inline=False)
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        await add_achievement(interaction.guild.id, interaction.user.id, "Statistics 2")
        await add_achievement(interaction.guild.id, interaction.user.id, "Application")


    async def check_level(self, interaction: discord.Interaction, member: discord.Member):
        """
        interaction menu function for member's level.

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        conn, cur = get_server_database(interaction.guild.id)

        cur.execute("SELECT * FROM level WHERE id = ?", (member.id,))
        result = cur.fetchone()

        if result is None:
            await interaction.response.send_message(
                content=f"{member.mention} has no exp yet.",
                ephemeral=True
            )
            conn.close()
        else:
            level = result[2]
            exp = result[1]
            pcent_exp = round(exp / 10, 2)
            total = result[3]
            target_data = total

            cur.execute("SELECT total, RANK() OVER (ORDER BY total DESC) AS rank FROM level")
            rows = cur.fetchall()

            rank = next((row[1] for row in rows if row[0] == target_data), None)

            cur.execute("SELECT COUNT(*) FROM level")
            row_count = cur.fetchone()[0]
            conn.close()

            embed = discord.Embed(title=f"{member.display_name}'s level", color=0x0000FF)
            embed.set_thumbnail(url=member.avatar)
            embed.add_field(name="Level:", value=level, inline=False)
            embed.add_field(name="Exp:", value=f"{pcent_exp}%", inline=False)
            embed.add_field(name="Rank:", value=f"#{rank}/{row_count}", inline=False)
            embed.add_field(name="User:", value=member, inline=False)

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        await add_achievement(interaction.guild.id, interaction.user.id, "Level")
        await add_achievement(interaction.guild.id, interaction.user.id, "Application")


    async def generate_stats(self, guild, member):
        """
        Function to generate member's stats

        Generate an embed with the following stats:
        messages sent, words written, characters written,
        emojis used, reactions, messages edited,
        messages deletes, voice sessions, voice time

        Args:
            guild as interaction.guild
            member as discord.Member

        Returns:
            normal_stats as discord.Embed
        """
        conn, cur = get_server_database(guild.id)

        cur.execute("SELECT * FROM stats WHERE id = ?", (member.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            return None

        normal_stats = discord.Embed(title=f"{member.display_name}'s stats", color=0x00ff00)
        normal_stats.set_thumbnail(url=member.avatar)
        normal_stats.add_field(name="Messages sent", value=result[1], inline=True)
        normal_stats.add_field(name="Words written", value=result[2], inline=True)
        normal_stats.add_field(name="Characters written", value=result[3], inline=True)
        normal_stats.add_field(name="Emojis used", value=result[4], inline=True)
        normal_stats.add_field(name="Reactions", value=result[5], inline=True)
        normal_stats.add_field(name="Messages edited", value=result[6], inline=True)
        normal_stats.add_field(name="Messages deleted", value=result[7], inline=True)
        if result[8]:
            normal_stats.add_field(name="Voice sessions:", value=result[8], inline=True)
            normal_stats.add_field(name="Voice time:", value=f"{result[9]} minutes", inline=True)
        normal_stats.add_field(name="User:", value=member, inline=False)

        return normal_stats


    async def generate_stats2(self, guild, member):
        """
        Function to generate member's stats number 2

        Generate an embed with the following stats:
        words per message, characters per message, characters per word,
        emojis per message, ratio edited/message, ratio deleted/message

        Args:
            guild as interaction.guild
            member as discord.Member

        Returns:
            average_stats as discord.Embed
        """
        conn, cur = get_server_database(guild.id)

        cur.execute("SELECT * FROM stats WHERE id = ?", (member.id,))
        result = cur.fetchone()
        conn.close()

        if result is None:
            return None

        word_message = round(result[2] / result[1], 2)
        characters_message = round(result[3] / result[1], 2)
        emojis_message = round(result[4] / result[1], 2)
        characters_word = round(result[3] / result[2], 2)
        edited_message = round(result[6] / result[1] * 100, 2)
        deleted_message = round(result[7] / result[1] * 100, 2)

        average_stats = discord.Embed(title=f"{member.display_name}'s stats", color=0x00ff00)
        average_stats.set_thumbnail(url=member.avatar)
        average_stats.add_field(name="Words per message", value=word_message, inline=True)
        average_stats.add_field(name="Characters per message", value=characters_message, inline=True)
        average_stats.add_field(name="Characters per words", value=characters_word, inline=True)
        average_stats.add_field(name="Emojis per message", value=emojis_message, inline=True)
        average_stats.add_field(name="Ratio edited/message", value=f"{edited_message}%", inline=True)
        average_stats.add_field(name="Ratio deleted/message", value=f"{deleted_message}%", inline=True)
        if result[8]:
            minutes_join = round(result[9] / result[8], 2)
            average_stats.add_field(name="Minutes per voice session", value=minutes_join, inline=True)
        average_stats.add_field(name="User:", value=member, inline=False)

        return average_stats


    async def generate_card(self, guild, member):
        """
        Function to generate member's activity card

        Generate an embed with the following fields:
        Level/Rank, fight stats, top role, top stats,
        achievements (1~10), achievements (11~20)

        Args:
            guild as interaction.guild
            member as discord.Member

        Returns:
            member_card as discord.Embed
        """
        conn, cur = get_server_database(guild.id)

        member_card = discord.Embed(
            title=f"{member}'s Profile",
            description=f"{member.mention} ({member.id})",
            color=0x808080
        )

        cur.execute("SELECT * FROM level WHERE id = ?", (member.id,))
        levels = cur.fetchone()

        level = levels[2] if levels else 0
        exp = levels[1] if levels else 0
        pcent_exp = round(exp / 10, 2) if levels else 0
        total = levels[3] if levels else 0

        _, liste_1, liste_2, total_achieves = (
            await get_achievements(guild.id, member.id)
        )
        member_top_stats = await self.top_stats(guild.id, member.id)
        member_top_stats = member_top_stats if member_top_stats else "None"
        member_top_role = (
            member.top_role.mention if member.top_role.id != guild.id else "None"
        )
        if total_achieves - 10 <= 0:
            total_achieves_1 = total_achieves
        else:
            total_achieves_1 = 10
            total_achieves_2 = total_achieves % 10
        cur.execute("SELECT total, RANK() OVER (ORDER BY total DESC) AS rank FROM level")
        ranks = cur.fetchall()
        if ranks:
            rank = next((row[1] for row in ranks if row[0] == total), 0)
            cur.execute("SELECT COUNT(*) FROM level")
            member_rank = f"{rank}/{cur.fetchone()[0]}"
        else:
            member_rank = "N/A"
        cur.execute("SELECT * FROM fightscore WHERE id = ?", (member.id,))
        fightstats = cur.fetchone()
        if fightstats:
            points = fightstats[1] if fightstats[1] else 0
            matches = fightstats[2] if fightstats[2] else 0
        else:
            points = 0
            matches = 0
        conn.close()
        member_card.add_field(
            name="Level / Rank",
            value=f"Level: {level} ({pcent_exp}%)\nRank: {member_rank}",
            inline=True
        )
        member_card.add_field(
            name="Fight stats",
            value=f"Duels: {matches}\nScore: {points}",
            inline=True
        )
        member_card.add_field(
            name="Top Role",
            value=member_top_role,
            inline=True
        )
        member_card.add_field(
            name="Top stats",
            value=member_top_stats,
            inline=True
        )
        member_card.add_field(
            name=f"Achievements ({total_achieves_1})",
            value=liste_1,
            inline=True
        )
        if liste_2:
            member_card.add_field(
                name=f"Achievements ({total_achieves_2})",
                value=liste_2,
                inline=True
            )
        member_card.set_thumbnail(url=member.display_avatar.url)

        return member_card


    async def all_stats(self, interaction: discord.Interaction, member: discord.Member):
        """
        interaction menu function for member's complete stats.

        Args:
            interaction as discord.Interaction
            member as discord.Member
        """
        normal_stats = await self.generate_stats(interaction.guild, member)
        average_stats = await self.generate_stats2(interaction.guild, member)
        member_card = await self.generate_card(interaction.guild, member)
        embeds = [
            embed for embed in [normal_stats, average_stats, member_card] if embed is not None
        ]
        await interaction.response.send_message(embeds=embeds, ephemeral=True)



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Stats(bot))
