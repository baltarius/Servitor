# bookmovie.py
"""
Cog to find informations about medias

Used to find informations about books and movies

Author: Elcoyote Solitaire
"""
import requests
import discord

from imdb import Cinemagoer
from discord import app_commands, Interaction
from discord.app_commands import Group
from discord.ext import commands
from cogs.intercogs import add_achievement



class Bookmovie(commands.Cog, name="bookmovie"):
    """
    Book and movie class

    Allows to find movie and book information
    from a title or from the ID of the media.

    Commands:
        /book

        Group movie:
            - find_movieid
            - info

    Args:
        None
    """
    def __init__(self, bot):
        self.bot = bot


    async def get_info_by_isbn(self, isbn):
        """
        Functions to fetch book information from an ISBN

        Args:
            isbn as digit for ISBN ID of a book

        Returns:
            book_info as a dictionnary
        """
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if f"ISBN:{isbn}" in data:
                raw_info = data[f"ISBN:{isbn}"]
                return raw_info

            return "No book found with this ISBN."

        return f"Error: {response.status_code}"


    async def search_isbn_by_title(self, title):
        """
        Search books by title

        Args:
            title as a string for the book's title

        Returns:
            books as a string of formatted results
        """
        url = f"https://openlibrary.org/search.json?title={title}"
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if "docs" in data and len(data["docs"]) > 0:
                raw_books = []
                for book in data["docs"][:5]:
                    raw_books.append({
                        "title": book.get("title", "N/A"),
                        "author": ", ".join(book.get("author_name", ["Unknown Author"])),
                        "publish_year": str(book.get("first_publish_year", "N/A")),
                        "isbn": book.get("isbn", ["N/A"])[0]
                    })
                books = ""
                for book in raw_books:
                    formatted_book = (
                        f"Title: {book['title']}\n"
                        f"Author: {book['author']}\n"
                        f"Publish Year: {book['publish_year']}\n"
                        f"ISBN: {book['isbn']}\n"
                    )
                    books += f"{formatted_book}\n"
                return books

            return "No books found with this title."

        return f"Error: {response.status_code}"


    async def parse_book_info(self, book_data):
        """
        Parses book information for embed purpose

        Args:
            book_data as a dictionary

        Returns:
            title, authors, num_pages, publish_date, data_isbn, publishers, cover_image
        """
        try:
            title = book_data.get('title', 'N/A')
            authors_data = book_data.get('authors', [])
            authors = ", ".join(
                [author.get('name', 'Unknown') for author in authors_data]
            )
            num_pages = book_data.get('number_of_pages', 'N/A')
            publish_date = book_data.get('publish_date', 'N/A')
            data_isbn = ", ".join(book_data.get('identifiers', {}).get('isbn_13', ['N/A']))
            publishers_data = book_data.get('publishers', [])
            publishers = ", ".join(
                [publisher.get('name', 'Unknown') for publisher in publishers_data]
            )
            cover_image = book_data.get('cover', {}).get('large', 'No cover image available')

            return title, authors, num_pages, publish_date, data_isbn, publishers, cover_image

        except ValueError as value_error:
            return f"Value Error: {str(value_error)}"

        except TypeError as type_error:
            return f"Type Error: {str(type_error)}"

        except AttributeError as attr_error:
            return f"Attribute Error: {str(attr_error)}"


    @app_commands.command(
        name="find_book",
        description="Find a book from ISBN or an ISBN from title"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        isbn="book's ISBN",
        title="book's title"
    )
    async def find_book(self, interaction: Interaction, isbn: str = None, title: str = None):
        """
        Command to find a book ISBN from a title or information from ISBN

        Takes in priority the ISBN to find the informations
        or the title to find a list of matches to get the ISBN

        Args:
            interaction as discord.Interaction
            isbn as a string of digits of the book's ISBN
            title as a string for the title of the book
        """
        if isbn is None and title is None:
            await interaction.response.send_message(
                content="Please provide either an ISBN or a title.",
                ephemeral=True
            )
            return
        if isbn is not None:
            isbn = isbn.strip().replace("-", "")
            if not isbn.isdigit():
                await interaction.response.send_message(
                    content="ISBN must be digits", ephemeral=True
                )
                return
        await interaction.response.send_message(
            content="Looking up information . . .",
            ephemeral=True
        )
        if title is None:
            book_info = await self.get_info_by_isbn(isbn)
            if not isinstance(book_info, dict):
                await interaction.edit_original_response(content=book_info)
                return
            title, authors, num_pages, publish_date, data_isbn, publishers, cover_image = (
                await self.parse_book_info(book_info)
            )
            embed = discord.Embed(title=isbn, color=0xffffff)
            embed_field = (
                f"Author(s): {authors}\nNumber of pages: {num_pages}"
                f"\nISBN: {data_isbn}\nPublishers: {publishers} ({publish_date})\n"
            )
            embed.set_thumbnail(url=cover_image)
            embed.add_field(name=title, value=embed_field, inline=True)

            await interaction.edit_original_response(content=f"Results: for {isbn}", embed=embed)
            return
        books = await self.search_isbn_by_title(title)
        await interaction.edit_original_response(content=books)


    @find_book.error
    async def find_book_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    movie_group = Group(
        name="movie", description="Group of command for movies", guild_only=True
    )


    @movie_group.command()
    @app_commands.checks.cooldown(10, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(movie_name="Enter the name of the movie")
    async def find_movieid(self, interaction: Interaction, movie_name: str):
        """
        Find the movie ID from a name

        Args:
            interaction as discord.Interaction
            movie_name as string for the movie's name
        """
        movies = Cinemagoer().search_movie(movie_name)
        list_movies = ""
        for movie in movies:
            list_movies += f"{movie}: {movie.movieID}\n"
        await interaction.response.send_message(
            content=f"Here's the match for {movie_name}\n{list_movies}",
            ephemeral=True
        )


    @movie_group.command()
    @app_commands.checks.cooldown(10, 3600.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(movie_id="Enter the movie's ID")
    async def info(self, interaction: Interaction, movie_id: int):
        """
        Find the movie infos from the movie's ID.

        Args:
            interaction as discord.Interaction
            movie_id as an integer for the movie's ID
        """
        await interaction.response.send_message(content="searching . . . ", ephemeral=True)
        movie = Cinemagoer().get_movie(movie_id)
        title = movie["title"]
        year = movie["year"]
        genres = ""
        try:
            for genre in movie["genre"]:
                genres += f"{genre} "
        except KeyError:
            genres = "Not available"
        try:
            cast = movie["cast"][:4]
        except KeyError:
            cast = "Not available"
        actors = ""
        if cast != "Not available":
            for actor in cast:
                actors += f"{actor}\n"
        try:
            runtimes = f"{movie['runtimes'][0]} minutes"
        except KeyError:
            runtimes = "Not Available"
        try:
            rating = f"{movie['rating']} / 10"
        except KeyError:
            rating = "Not available"
        try:
            plot = movie["plot outline"]
        except KeyError:
            plot = "Not available"
        embed = discord.Embed(
            title=f"{title} - {year} ({movie_id})",
            color=0xFFD700,
            description=""
        )
        embed.set_thumbnail(url=movie["full-size cover url"])
        embed.add_field(
            name=f"Genre: {genres}\nDuration: {runtimes}\nRating {rating}",
            value="",
            inline=True
        )
        embed.add_field(
            name="Casting (first 4 actors):",
            value=actors,
            inline=True
        )
        embed.add_field(
            name="Plot:",
            value=plot,
            inline=False
        )
        await interaction.edit_original_response(content="", embed=embed)


    @find_movieid.error
    async def find_movieid_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    @info.error
    async def info_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Bookmovie(bot))
