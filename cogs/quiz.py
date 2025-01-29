# quiz.py
"""
Small member quiz game.

This cog is for the quiz game, which
includes the commands, timers and automatic
database for the quiz to go on.

DO NOT LOAD THIS COG IF YOU THE BOT IS
ON OVER 100 SERVERS. THAT WOULD DRAIN A
LOT OF RESSOURCES FROM THE ENVIRONMENT.

Author: Elcoyote Solitaire
"""
import datetime
import asyncio
import difflib
import random
import re
import json
import pytz

from datetime import datetime, timedelta
from discord import app_commands, Interaction
from discord.ext import commands, tasks
from cogs.intercogs import get_server_database, get_time_zone, get_setup_chan_id



class Quiz(commands.Cog, name="quiz"):
    """
    Class for the quiz game.

    This class contains commands, timers and
    automatic database for the quiz' system.

    Commands:
        /quiz

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot
        self.guild_quiz_data = {}
        self.quiz_tasks = {}
        self.trivia = False
        self.title = ""


    async def after_on_ready(self):
        await self.bot.wait_until_ready()
        await self.load_quiz_data()


    async def cog_load(self):
        asyncio.create_task(self.after_on_ready())


    async def cog_unload(self):
        self.run_trivia.cancel()


    async def load_quiz_data(self):
        """
        Loads all datas for quiz game
        """
        for guild in self.bot.guilds:
            self.guild_quiz_data[guild.id] = {
                "starter": "",
                "question": "",
                "answer": "",
                "quizchan": "",
                "timestamp": ""
            }
            self.quiz_tasks[guild.id] = ""
            conn, cur = get_server_database(guild.id)
            cur.execute("SELECT id FROM setup WHERE chans = ?", ("quiz",))
            quizchan_id = cur.fetchone()
            if quizchan_id:
                self.guild_quiz_data[guild.id]["quizchan"] = quizchan_id[0]
                cur.execute("SELECT * FROM quiz")
                quiz_data = cur.fetchall()
                if quiz_data:
                    self.guild_quiz_data[guild.id]["starter"] = quiz_data[0][0]
                    self.guild_quiz_data[guild.id]["question"] = quiz_data[0][1]
                    self.guild_quiz_data[guild.id]["answer"] = quiz_data[0][2]
                    self.guild_quiz_data[guild.id]["timestamp"] = quiz_data[0][3]
                    cur.execute("SELECT timezone FROM timezone")
                    row = cur.fetchone()
                    conn.close()
                    time_zone = (
                        pytz.timezone(row[0]) if row is not None else pytz.timezone("US/Eastern")
                    )
                    time_now = (
                        datetime.strptime(datetime.now(time_zone).strftime("%Y-%m-%d %H:%M:%S"),
                        "%Y-%m-%d %H:%M:%S")
                    )
                    timestamp = (
                        datetime.strptime(self.guild_quiz_data[guild.id]["timestamp"],
                        "%Y-%m-%d %H:%M:%S")
                    )
                    time_diff = time_now - timestamp
                    if time_diff > timedelta(hours=24):
                        asyncio.create_task(self.reset_quiz(guild.id, "timeout", "ah"))
                    else:
                        time_left = timedelta(hours=24) - time_diff
                        seconds_left = time_left.total_seconds()
                        self.quiz_tasks[guild.id] = (
                            asyncio.create_task(self.quiz_timer(guild.id, seconds_left))
                        )
                else:
                    conn.close()
            else:
                conn.close()


    async def quiz_timer(self, guild_id, seconds_left):
        """
        Timer that waits for the remaining time and resets the quiz when time is up.
        """
        try:
            await asyncio.sleep(seconds_left)
            await self.reset_quiz(guild_id, "timeout", "Time's up!")
        except asyncio.CancelledError:
            pass


    async def reset_quiz(self, guild_id, time_answer, author):
        """
        Resets the quiz datas from self.variables and guild's database

        Used by:
            on_message

        Args:
            guild_id as guild.id
        """
        quiz_data = self.guild_quiz_data[guild_id]
        channel = self.bot.get_channel(int(self.guild_quiz_data[guild_id]["quizchan"]))
        if time_answer == "timeout":
            await channel.send(
                f"Le temps est écoulé. __<@{quiz_data['starter']}>__ avait demandé\nQuestion: "
                f"__{quiz_data['question']}__\nRéponse: __{quiz_data['answer']}__"
            )
        if time_answer == "answer":
            await channel.send(
                f"GG {author.mention}! La bonne réponse était effectivement "
                f"__{quiz_data['answer']}__.\nLa question était: __{quiz_data['question']}__\n"
                "À toi de relancer la partie avec /quiz_start"
            )
        self.guild_quiz_data[guild_id]["starter"] = ""
        self.guild_quiz_data[guild_id]["question"] = ""
        self.guild_quiz_data[guild_id]["answer"] = ""
        self.guild_quiz_data[guild_id]["timestamp"] = ""
        try:
            self.quiz_tasks[guild_id].cancel()
        except AttributeError:
            pass
        conn, cur = get_server_database(guild_id)
        cur.execute("DELETE FROM quiz")
        conn.commit()
        conn.close()


    async def add_score_point(self, guild_id, user_id, score):
        """
        Add scores to the database
        """
        conn, cur = get_server_database(guild_id)
        cur.execute("SELECT * FROM quiz_score WHERE id = ?", (user_id,))
        scores = cur.fetchall()
        if not scores:
            if score == "question":
                cur.execute("INSERT INTO quiz_score (id, score, question) VALUES (?, ?, ?)",
                    (user_id, 0, 1)
                )
                conn.commit()
                conn.close()
                return

            cur.execute("INSERT INTO quiz_score (id, score, question) VALUES (?, ?, ?)",
                (user_id, 1, 0)
            )
            conn.commit()
            conn.close()
            return

        current_score = scores[0][1]
        current_question = scores[0][2]
        if score == "question":
            new_score = current_score
            new_question = current_question + 1
        elif score == "score":
            new_score = current_score + 1
            new_question = current_question
        cur.execute("UPDATE quiz_score SET score = ?, question = ? WHERE id = ?",
            (new_score, new_question, user_id)
        )
        conn.commit()
        conn.close()


    @app_commands.command(
        name="quiz_start",
        description="Enter your question and the answer for the quiz"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(10, 21600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(
        question="What is the question?",
        answer="What it the answer?"
    )
    async def quiz_start(self, interaction: Interaction, question: str, answer: str):
        """
        Starts the quiz
        """
        quiz_chan = await get_setup_chan_id(interaction.guild.id, "quiz")
        if quiz_chan is not None:
            self.guild_quiz_data[interaction.guild.id]["quizchan"] = quiz_chan
        if not self.guild_quiz_data[interaction.guild.id]["quizchan"]:
            await interaction.response.send_message(
                content="The quiz' channel is not yet setup. Please contact an admin.",
                ephemeral=True
            )
            return
        if self.guild_quiz_data[interaction.guild.id]["starter"]:
            await interaction.response.send_message(
                content="There's already a quiz going.\nQuestion: "
                f"{self.guild_quiz_data[interaction.guild.id]['question']}",
                ephemeral=True
            )
            return
        if len(question) > 500:
            await interaction.response.send_message(
                content=f"Please restrict your question to max 500 characters ({len(question)}).",
                ephemeral=True
            )
        if len(answer) > 100:
            await interaction.response.send_message(
                content=f"Please restrict your answer to max 100 characters ({len(answer)}).",
                ephemeral=True
            )
        time_zone = await get_time_zone(interaction.guild.id)
        time_now = datetime.now(time_zone).strftime("%Y-%m-%d %H:%M:%S")
        conn, cur = get_server_database(interaction.guild.id)
        cur.execute(
            "INSERT INTO quiz (starter, question, answer, timestamp) VALUES (?, ?, ?, ?)",
            (interaction.user.id, question.lower(), answer.lower(), time_now)
        )
        conn.commit()
        cur.execute("SELECT id FROM setup WHERE chans = ?", ("quiz",))
        quizchan_id = cur.fetchone()
        conn.close()
        self.guild_quiz_data[interaction.guild.id]["starter"] = interaction.user.id
        self.guild_quiz_data[interaction.guild.id]["question"] = question.lower()
        self.guild_quiz_data[interaction.guild.id]["answer"] = answer.lower()
        self.guild_quiz_data[interaction.guild.id]["timestamp"] = time_now
        channel = self.bot.get_channel(quizchan_id[0])
        await self.add_score_point(interaction.guild.id, interaction.user.id, "question")
        await interaction.response.send_message(
            content=f"Your question has been sent to {channel.mention}\nQuestion: "
            f"__{question}__\nAnswer:__{answer}__",
            ephemeral=True
        )
        await channel.send(f"Nouvelle question de {interaction.user.mention}:\n{question}")
        self.quiz_tasks[interaction.guild.id] = (
            asyncio.create_task(self.quiz_timer(interaction.guild.id, 86400))
        )


    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listener for messages.

        Triggers when the channel is the quiz channel
        and the correct answer is given by a member.

        Args:
            message: The message.
        """
        if message.author.bot:
            return
        if message.author.id == self.guild_quiz_data[message.channel.guild.id]["starter"] and self.trivia is False:
            return
        quiz_data = self.guild_quiz_data[message.channel.guild.id]
        if message.channel.id == quiz_data["quizchan"]:
            if str(self.guild_quiz_data[message.channel.guild.id]["starter"]).strip() is not None:
                if quiz_data["answer"].lower() == message.content.lower():
                    await self.reset_quiz(message.channel.guild.id, "answer", message.author)
                    await self.add_score_point(message.channel.guild.id, message.author.id, "score")
                    return
                matcher = difflib.SequenceMatcher(
                    None, quiz_data["answer"].lower(), message.content.lower()
                )
                if matcher.ratio() * 100 >= 90.0:
                    await self.add_score_point(message.channel.guild.id, message.author.id, "score")
                    await self.reset_quiz(message.channel.guild.id, "answer", message.author)
            if self.trivia is True:
                matcher = difflib.SequenceMatcher(
                    None, self.title.lower(), message.content.lower()
                )
                if matcher.ratio() * 100 >= 80.0:
                    self.trivia = False
                    self.run_trivia.cancel()
                    await message.channel.send(
                        content=f"GG {message.author.mention}! The answer was __**{self.title}**__"
                    )
                    self.title = ""


    async def generate_trivia(self):
        """
        Select a random movie from the json
        file and generate the trivia from it

        Args:
            None

        Returns:
            first_hint, second_hint, third_hint, fourth_hint
        """
        with open("./movie/movies_data.json", "r", encoding="utf-8") as file:
            movies = json.load(file)

        filtered_movies = [
            movie for movie in movies
            if re.compile("^[A-Za-z0-9 ]+$").match(movie["title"])
            and movie["genre"] != "N/A"
            and "Adult" not in movie["genre"]
            and movie.get("runtimes")
            and len(movie["runtimes"]) > 0
            and movie["runtimes"][0].isdigit()
            and int(movie["runtimes"][0]) >= 60
            and len(movie["plot_outline"]) > 3
        ]

        selected_movie = random.choice(filtered_movies)

        self.title = selected_movie["title"]
        genre = ", ".join(selected_movie["genre"])
        year = f"Year: {selected_movie['year']}"
        #decade = (selected_movie["year"] // 10) * 10
        main_actor = selected_movie["cast"][0] if selected_movie["cast"] else "Unknown"
        supporting_actors_list = (
            selected_movie['cast'][1:4] if len(selected_movie['cast']) > 1
            else 'No supporting actor'
        )
        supporting_actors = " ".join(supporting_actors_list)
        supporting_actors = f"Supporting actors: {supporting_actors}"
        runtime = f"Runtime: {selected_movie['runtimes'][0]} minutes"
        rating = f"Ratings: {selected_movie['rating']}"
        if selected_movie["plot_outline"] != "N/A":
            plot_words = ([
                word for word in selected_movie["plot_outline"].split()
                if len(word) >= 5 and word.isalpha()
            ])
            if len(plot_words) >= 5:
                hint_words = random.sample(plot_words, 5)
            else:
                hint_words = plot_words
        else:
            hint_words = selected_movie["plot_outline"]
        plot_hint = f"Random words from the plot: {' '.join(hint_words).lower()}"
        first_hint = f"Genre(s): {genre}\nYears: {(selected_movie['year'] // 10) * 10}'s"
        #hint_options = [supporting_actors, runtime, rating, plot_hint, year]
        random_hint = random.sample([supporting_actors, runtime, rating, plot_hint, year], 4)
        second_hint = f"Second hint\n{random_hint[0]}\n{random_hint[1]}"
        third_hint = f"Third hint\nMain actor: {main_actor}"
        fourth_hint = f"Last hint:\n{random_hint[2]}\n{random_hint[3]}"
        print(first_hint, second_hint, third_hint, fourth_hint)
        return first_hint, second_hint, third_hint, fourth_hint


    @app_commands.command(
        name="trivia",
        description="Start a trivia for movies"
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(10, 21600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe()
    async def trivia(self, interaction: Interaction):
        """
        Starts a trivia with a random movie from movies_data.json

        Uses:
            generate_trivia()

        Args:
            interaction as discord.Interaction
        """
        if self.trivia is True:
            await interaction.response.send_message(
                content="There's already a trivia running",
                ephemeral=True
            )
            return

        quiz_chan = await get_setup_chan_id(interaction.guild.id, "quiz")
        if quiz_chan is not None:
            self.guild_quiz_data[interaction.guild.id]["quizchan"] = quiz_chan
        if not self.guild_quiz_data[interaction.guild.id]["quizchan"]:
            await interaction.response.send_message(
                content="The quiz' channel is not yet setup. Please contact an admin.",
                ephemeral=True
            )
            return
        self.trivia = True
        await interaction.response.send_message(
            content="Gathering information. The first hint will be sent shortly.",
            ephemeral=True
        )
        first_hint, second_hint, third_hint, fourth_hint = await self.generate_trivia()
        channel = self.bot.get_channel(quiz_chan)
        self.run_trivia.start(
            channel, interaction.user.mention, first_hint, second_hint, third_hint, fourth_hint
        )


    @tasks.loop(count=1)
    async def run_trivia(self, channel, user, first_hint, second_hint, third_hint, fourth_hint):
        """
        Task to run the hints' loop
        """
        await channel.send(
            content=f"{user} started a trivia! "
            f"Here's the first hint to find the movie\n{first_hint}"
        )
        await asyncio.sleep(120)
        if self.trivia is True:
            await channel.send(content=second_hint)
        else:
            self.title = ""
            self.run_trivia.cancel()
            return
        await asyncio.sleep(120)
        if self.trivia is True:
            await channel.send(content=third_hint)
        else:
            self.title = ""
            self.run_trivia.cancel()
            return
        await asyncio.sleep(120)
        if self.trivia is True:
            await channel.send(content=fourth_hint)
        else:
            self.title = ""
            self.run_trivia.cancel()
            return
        await asyncio.sleep(120)
        self.trivia = False
        await channel.send(
            content=f"Time's up! The answer was __**{self.title}**__"
        )
        self.title = ""



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Quiz(bot))
