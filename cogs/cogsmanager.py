# cogsmanager.py
"""
Functions for managing cogs.

This file contains what is needed to
load, unload and reload cogs and sync
your commands with discord.

Author: Elcoyote Solitaire

sync command from Umbra:
https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html
"""
import os
import discord

from typing import Literal, Optional
from discord.ext import commands



class Cogsmanager(commands.Cog, name="cogsmanager"):
    """
    Cogs manager.

    This class contains commands to load, unload and
    reload cogs.
    
    Commands:
        !load
        !unload
        !reload
        !showcogs
        !sync
    """
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    @commands.is_owner()
    async def load(self, ctx: commands.Context, cog_name: str):
        """
        Loads a specified cog to the bot.

        Args:
            ctx as commands.Context
            cog_name (str): The name of the cog to load.

        Raises:
            commands.ExtensionFailed: If loading the cog fails.
        """
        if cog_name != "cogsmanager":
            try:
                await self.bot.load_extension(f"cogs.{cog_name}")
                await ctx.send(f"{cog_name} cog has been loaded.")
            except commands.ExtensionFailed as extension_failed:
                await ctx.send(f"Error loading {cog_name} cog: {extension_failed}")
        else:
            await ctx.send("cogsmanager is already loaded, obviously.")


    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, cog_name: str):
        """
        Unloads a specified cog from the bot.

        Args:
            ctx as commands.Context
            cog_name (str): The name of the cog to unload.

        Raises:
            commands.ExtensionNotLoaded: If the specified cog is not loaded.
            commands.ExtensionFailed: If unloading the cog fails.
        """
        if cog_name != "cogsmanager":
            try:
                await self.bot.unload_extension(f"cogs.{cog_name}")
                await ctx.send(f"{cog_name} cog has been unloaded.")
            except commands.ExtensionFailed as extension_failed:
                await ctx.send(f"Error unloading {cog_name} cog: {extension_failed}")
        else:
            await ctx.send("I can't unload the cogsmanager.")


    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, cog_name: str):
        """
        Unloads a specified cog from the bot then loads it back.

        Args:
            ctx as commands.Context
            cog_name (str): The name of the cog to unload.

        Raises:
            commands.ExtensionNotLoaded: If the specified cog is not loaded.
            commands.ExtensionFailed: If reloading the cog fails.
        """
        if cog_name != "cogsmanager":
            try:
                await self.bot.unload_extension(f"cogs.{cog_name}")
                await self.bot.load_extension(f"cogs.{cog_name}")
                await ctx.send(f"{cog_name} cog has been reloaded.")
            except commands.ExtensionFailed as extension_failed:
                await ctx.send(f"Error reloading {cog_name} cog: {extension_failed}")
        else:
            await ctx.send("I can't reload the cogsmanager.")


    @commands.command()
    @commands.is_owner()
    async def sync(
        self, ctx: commands.Context, guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        """
        Function to sync commands.

        Please note that using sync takes a few minutes to be fully effective
        on all the bot's servers. To force the sync, use those in order:
        !sync  >>  !sync *  >>  !sync ^

        Examples:
            !sync
                This takes all global commands within the CommandTree
                and sends them to Discord. (see CommandTree for more info.)
            !sync ~
                This will sync all guild commands for the current context’s guild.
            !sync *
                This command copies all global commands to the current
                guild (within the CommandTree) and syncs.
            !sync ^
                This command will remove all guild commands from the CommandTree
                and syncs, which effectively removes all commands from the guild.
            !sync 123 456 789
                This command will sync the 3 guild ids we passed: 123, 456 and 789.
                Only their guilds and guild-bound commands.

        Args:
            ctx as context
            guilds: guild(s) to sync
            spec: optional with 1 argument only
        """
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} cmds {'globally' if spec is None else 'to current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


    def count_lines(self, file_path):
        """
        Counts the amount of lines per cogs.

        This function is used in the command "showcogs"
        """
        with open(file_path, "r", encoding="utf-8") as file:
            line_count = sum(1 for line in file)
        return line_count


    @commands.command()
    @commands.is_owner()
    async def showcogs(self, ctx: commands.Context):
        """
        Shows the current cogs loaded.

        Args:
            ctx as commands.Context
        """
        response = ""
        cog_lines_total = 0
        c_cogs = 0
        for cog in self.bot.cogs:
            cog_file = f"{cog}.py"
            extension_file_path = os.path.join("./cogs", cog_file)
            cog_lines = self.count_lines(extension_file_path)
            cog_lines_total += cog_lines
            c_cogs += 1
            response += f"{cog} : {cog_lines}\n"

        await ctx.send(
            "List of the loaded cogs:\n"
            f"{response}\n Total: {c_cogs} cogs, {cog_lines_total} lines."
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Cogsmanager(bot))
