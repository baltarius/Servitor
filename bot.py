# bot.py
"""
Core code of the bot.

This is where the bot starts. It loads all the cogs and the
main configuration. In your command terminal, type: python bot.py

Author: Elcoyote Solitaire
"""
import os
import logging
import logging.handlers
import json
import platform
import random
import sys
import discord

from logging.handlers import RotatingFileHandler
from datetime import datetime
from dotenv import load_dotenv
from discord import app_commands
from discord.ext import commands, tasks
from cogs.intercogs import add_achievement


def load_configs():
    """
    Allow to load configs from config.json
    on start, then reload at intervals

    Returns:
        config:
            [prefix]
            [status_interval_minutes]
            [custom_statuses]
            [playing_statuses]
    """
    with open("config.json", "r", encoding="utf-8") as jsonfile:
        config = json.load(jsonfile)
        return config


if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")


os.makedirs("./database/servers", exist_ok=True)
os.makedirs("./cogs", exist_ok=True)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True



class MyBot(commands.Bot):
    """
    Custom Discord bot class.

    This class extends the commands.Bot class to provide additional functionality.
    This is a setup to override the setup_hook to includes specific asyncs and loops.

    Args:
        command_prefix (str): The prefix for bot commands.
        intents (discord.Intents): The intents for the bot.
        help_command: The custom help command instance.
    """
    def __init__(self, config, status_interval, help_command=None):
        self.config = config
        self.status_interval = status_interval
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents
        )
        self.original_app_error = self.tree.on_error
        self.tree.on_error = self.on_app_command_error

    
    def count_lines(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            line_count = sum(1 for line in file)
        return line_count


    async def setup_hook(self) -> None:
        """
        Overriding the normal setup_hook.
        """
        totallines = 0
        totalextensions = 0
        print("\n-----EXTENSIONS-----")
        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    extension_file_path = os.path.join("./cogs", file)
                    lines = self.count_lines(extension_file_path)
                    print(f"Loaded extension '{extension}' ({lines} lines)")
                    totallines += lines
                    totalextensions += 1
                except commands.ExtensionFailed as extension_failed:
                    exception = f"{type(extension_failed).__name__}: {extension_failed}"
                    print(f"Failed to load extension {extension}\n{exception}")
        print(f"¤¤¤ {totallines} lines of codes for {totalextensions} extensions ¤¤¤")
        #self.add_view(PersistentView())


    async def on_ready(self):
        """
        Print the general informations in the console/command terminal.
        """
        activeservers = self.guilds
        print("\n-----SYS INFOS-----")
        print(f"discord.py API version: {discord.__version__}")
        print(f"Python version: {platform.python_version()}")
        print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        print("\n-----BOT NAME-----")
        print(f"{self.user.name} (ping:{round(self.latency * 1000)}ms)")
        print("\n-----SERVERS-----")
        for guild in activeservers:
            print(f"- {guild.name} (ID: {guild.id}) ({guild.member_count} members)")
        print("-------------------")
        print("Bot is now online and ready")
        self.status_task.start()


    @tasks.loop(minutes=10)
    async def status_task(self):
        """
        Setup the game status task of the bot
        
        Half/half chance to get a random status or random custom activity.
        """
        self.config = load_configs()
        bot_presence = random.choice([True, False])
        statuses = self.config.get("custom_statuses", [])
        playing = self.config.get("playing_statuses", [])
        if not playing or not statuses:
            await self.change_presence(activity=discord.Game("loading status from config . . ."))
        else:
            if bot_presence:
                await self.change_presence(activity=discord.Game(random.choice(playing)))
            else:
                await self.change_presence(
                    activity=discord.CustomActivity(name=random.choice(statuses))
                )


    async def on_app_command_error(
        self, interaction: discord.Interaction[commands.Bot], error: app_commands.AppCommandError,
    ) -> None:
        """
        Global error handler for application commands.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.CommandOnCooldown):
            await add_achievement(interaction.guild.id, interaction.user.id, "Cooldown!")
            cooldown_seconds = error.retry_after
            hours = int(cooldown_seconds // 3600)
            minutes = int((cooldown_seconds % 3600) // 60)
            seconds = int(cooldown_seconds % 60)
            cooldown_message = "You are on cooldown. Try again in "
            if hours > 0:
                cooldown_message += f"{hours}h "
            if minutes > 0:
                cooldown_message += f"{minutes}m "
            cooldown_message += f"{seconds}s."
            await interaction.response.send_message(
                content=cooldown_message,
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.MissingRole):
            await interaction.response.send_message(
                "You do not have the required role to use this command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.CheckFailure):
            await interaction.response.send_message(
                "I don't have the permissions to perform that command.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.CommandNotFound):
            await interaction.response.send_message(
                "This command does not exist.",
                ephemeral=True
            )
            return
        if isinstance(error, app_commands.errors.CommandInvokeError):
            await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
            await interaction.response.send_message(
                "An internal error occurred while executing the command.",
                ephemeral=True
            )
            print(f"Unexpected error: {error}")
            return
        if isinstance(error, app_commands.errors.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the required permissions to run this command!",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )
        print(
            f"{datetime.now().strftime('%H:%M:%S')} - Error in {interaction.guild.name}\n"
            f"User: {interaction.user.display_name}\nError: {error}"
        )


def main():
    """
    Starts the bot and the logs system (discord.log)
    """
    # get token from .env file
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')

    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(
        '[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    config = load_configs()
    status_interval = config.get("status_interval_minutes", 10)
    bot = MyBot(config, status_interval)
    bot.run(token, log_handler=handler)



if __name__ == "__main__":
    main()
