# anonyme.py
"""
Cog for anonymous system. Allows to assign a
permanent nickname to users for followup on
future conversations. It is possible to reset
a nickname if an identity is revealed by
mistake or by guessing.

Note: only a limited amount of nicknames are
available, but the possibilities can be increased
by adding more common nouns and adjectives.

Author: Elcoyote Solitaire
"""
import random
import discord

from discord import app_commands, Interaction
from discord.ext import commands
from cogs.intercogs import get_server_database, add_achievement, get_setup_chan_id



class Anonyme(commands.Cog, name="anonyme"):
    """
    Anonymous class for anonymous system

    This class contains commands and list of nouns
    used to create anonymous names and send
    anonymous messages in a dedicated channel.

    Functions:
        get_pseudo()

    Commands:
        /anonyme
        /anonyme_reset
    """
    def __init__(self, bot):
        self.bot = bot


    common_nouns = [
        "apple", "arm", "army", "bag", "ball", "bank", "bar", "bed", "bell", "bird", "boat",
        "bottle", "box", "boy", "branch", "bridge", "brother", "bus", "cage", "cake", "camera",
        "camp", "car", "cat", "chair", "cheese", "child", "circle", "clock", "cloud", "coat",
        "coin", "color", "comb", "cow", "cup", "day", "desk", "dog", "door", "dream", "dress",
        "egg", "engine", "eye", "face", "farm", "feather", "finger", "fish", "flag", "floor",
        "flower", "forest", "friend", "game", "garden", "girl", "glass", "goat", "grain", "grass",
        "ground", "hair", "hand", "hat", "head", "heart", "hill", "horse", "house", "island",
        "jewel", "key", "king", "kitchen", "kite", "knife", "lamp", "leaf", "leg", "letter",
        "line", "lion", "lock", "map", "market", "meadow", "milk", "mirror", "money", "moon",
        "mountain", "mouse", "mouth", "needle", "night", "nose", "ocean", "office", "orange",
        "owl", "painter", "paper", "park", "pencil", "picture", "pig", "plane", "plant", "plate",
        "playground", "pocket", "poem", "pond", "queen", "rabbit", "rain", "river", "road",
        "rock", "room", "rope", "rose", "school", "sea", "sheep", "ship", "shoe", "shop", "sky",
        "snake", "snow", "song", "spoon", "star", "stone", "street", "sun", "table", "teacher",
        "team", "telephone", "television", "temple", "tent", "tiger", "town", "train", "tree",
        "truck", "umbrella", "vase", "village", "wall", "watch", "water", "whale", "wheel",
        "wind", "window", "wing", "wolf", "wood", "world", "year", "zebra", "book"
    ]


    adjectives = [
        "able", "adorable", "angry", "anxious", "awesome", "bad", "beautiful", "big", "bitter",
        "black", "blue", "bold", "boring", "brave", "bright", "brilliant", "broad", "busy",
        "calm", "careful", "charming", "cheap", "cheerful", "clean", "clever", "cold", "colorful",
        "comfortable", "confident", "cool", "crazy", "creative", "curious", "cute", "dark",
        "daring", "delicate", "delicious", "difficult", "dirty", "dizzy", "eager", "early",
        "easy", "elegant", "emotional", "empty", "energetic", "enormous", "excited", "fabulous",
        "famous", "fast", "fat", "fearless", "fiery", "firm", "flat", "fluffy", "foolish",
        "fragile", "fresh", "friendly", "funny", "gentle", "giant", "glorious", "gorgeous",
        "graceful", "green", "happy", "hard", "harsh", "healthy", "heavy", "helpful", "high",
        "honest", "hot", "humble", "hungry", "icy", "important", "impressive", "innocent",
        "interesting", "jealous", "kind", "large", "lazy", "light", "lively", "lonely", "long",
        "loud", "lovely", "lucky", "mad", "magnificent", "mighty", "modern", "narrow", "nervous",
        "nice", "noisy", "old", "ordinary", "perfect", "pink", "pleasant", "polite", "poor",
        "powerful", "pretty", "proud", "quick", "quiet", "rare", "red", "rich", "rough", "round",
        "sad", "safe", "salty", "scared", "shiny", "short", "shy", "silly", "simple", "skinny",
        "slow", "small", "smart", "smooth", "soft", "special", "square", "strong", "stupid",
        "successful", "sweet", "tall", "tame", "tasty", "thin", "tiny", "tough", "ugly",
        "unique", "valuable", "warm", "weak", "wet", "white", "wide", "wild", "wise", "wonderful",
        "yellow", "young", "yummy", "zealous"
    ]


    async def get_pseudo(self, guild_id, member_id):
        conn, cur = get_server_database(guild_id)
        cur.execute("SELECT prefix, suffix FROM anonyme WHERE id = ?", (member_id,))
        pseudos = cur.fetchone()
        if pseudos is not None:
            conn.close()
            return pseudos[0], pseudos[1]

        exist_prefix = True
        exist_suffix = True
        cur.execute("SELECT * FROM anonyme")
        anonymes = cur.fetchall()
        while exist_prefix:
            prefix = random.choice(self.common_nouns)
            if prefix not in anonymes:
                exist_prefix = False
        while exist_suffix:
            suffix = random.choice(self.adjectives)
            if suffix not in anonymes:
                exist_suffix = False
        cur.execute(
            "INSERT INTO anonyme (id, prefix, suffix) VALUES(?, ?, ?)", (member_id, prefix, suffix)
        )
        conn.commit()
        conn.close()
        return prefix, suffix


    @app_commands.command(
        name="anonyme",
        description="Sends an anonymous message in a dedicated channel"
    )
    @app_commands.guild_only()
    @app_commands.describe(msg="Your anonymous message")
    async def anonyme(self, interaction: Interaction, msg: str):
        """
        Anonymous communication command

        This command requires a dedicated channel and uses a
        max of 1500 characters per message to avoid any error
        on the bot. A random nick is automatically associated
        to the user, which will be permanent for future references.

        Args:
            msg: anonymous message with a maximum of 1500 characters
        """
        channel_id = await get_setup_chan_id(interaction.guild.id, "anonyme")
        if channel_id:
            channel = self.bot.get_channel(channel_id)
        else:
            await interaction.response.send_message(
                content="There's no dedicated channel for the anonyme's system. "
                "Please contact an admin",
                ephemeral=True
            )
            return
        if len(msg) > 1500:
            await interaction.response.send_message(
                content="Your message is too long to be sent to the anonymous channel."
                f"\n{len(msg)}/1500",
                ephemeral=True
            )
            return
        prefix, suffix = await self.get_pseudo(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(
            content=f"Your message has been sent to {channel.mention}.", ephemeral=True
        )
        await channel.send(content=f"Anonymous message:\n\"{msg}\"\n- {prefix} {suffix}")


    @app_commands.command(
        name="anonyme_reset",
        description="Resets a member's pseudo from the database"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.describe(
        prefix="Pseudo's prefix",
        suffix="Pseudo's suffix"
    )
    async def anonyme_reset(self, interaction: Interaction, prefix: str, suffix: str):
        """
        Command to reset someone's pseudo

        This command resets a member's pseudo using the prefix
        and suffix to keep the member's identity anonyme.

        Args:
            prefix as str
            suffix as str
        """
        prefix = prefix.lower()
        suffix = suffix.lower()
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute("DELETE FROM anonyme WHERE prefix = ? AND suffix = ?", (prefix, suffix))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            content=f"The pseudo {prefix} {suffix} has been reset.", ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Anonyme(bot))
