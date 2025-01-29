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

from discord.ext import commands, tasks
from dotenv import load_dotenv


if not os.path.isfile("config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open("config.json", "r", encoding="utf-8") as jsonfile:
        config = json.load(jsonfile)


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
    def __init__(self, help_command=None):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config["prefix"]),
            intents=intents
        )


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
        bot_presence = random.choice([True, False])
        statuses = [
            "I am a ro...application",
            "Bin there, bot that.",
            "Delicious bot: app-etizer",
            "I'm the alpha and omg",
            "Playing-yang"
        ]
        playing = [
            "The song of my people",
            "In my sandbox",
            "Tic-tac-toe with 0s and 1s",
            "Hide & seek with bugs",
            "Python and ladders",
            "or not playing...",
            "monopoly, losing friends",
            "Clue with mr. White in the studio",
            "Skribbl.idiot",
            "Gartic not fun",
            "Scrabble in binary",
            "Notepad PvP mode",
            "Fax and furious"
        ]
        if bot_presence:
            await self.change_presence(activity=discord.Game(random.choice(playing)))
        else:
            await self.change_presence(
                activity=discord.CustomActivity(name=random.choice(statuses))
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

    bot.run(token, log_handler=handler)


bot = MyBot()


if __name__ == "__main__":
    main()
