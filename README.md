# Servitor

Basic discord bot
A simple Discord bot by a python learner to python learners.

Feel free to contact me for more informations or to participate
in the developping of the project. 

This bot is intended to learn about python and how to develop
bots on Discord. If you are to participate, please note that
this is the main idea where we share the knowledge so people
can learn with exemples and make experiences on their own.


A HUGE thank you to the discord.py community is in order.
You guys are the best!


NOTE: if you installed python 3.13 or above, you have to perform this installation:
- pip install audioop-lts


How to get started (assuming you already installed python 3.9 or higher):

- Open a terminal (Start > run > cmd)
- Use the command line to go to the bot directory
- pip install -r requirements.txt

- Open the bot directory in File Explorer
- Edit (notepad) the file .env
- Insert your bot token in the file
- Save it and exit
- Open a terminal (Start > run > cmd)
- Go to the bot directory
- type: python bot.py




./ : all the primary files, which should not be modified except for the token and the prefix
- .env : contains your bot's TOKEN
- bot.py : the main file to start the bot
- config.json : contains mainly the prefix used by the bot
- README.md : Gets you started
- requirements.txt : used with "pip install -r requirements" to install all dependencies at once

./cogs : contains all the code files. Any addition of code should be placed there
- cogsmanager.py : used to load/reload/unload cog files and !sync commands
- intercogs.py : used to store codes that will be used across other cogs

./database/servers : contains the databases per server ID


Any additional cogs from the ./cogs folder are "add-ons" that are fully modular,
which means that you can keep them or flush them at will. All the cogs have all
the docstrings necessary to help you understand what they are used for. Feel free
to edit those files to match your needs.
