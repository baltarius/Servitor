# teambuilder.py
"""
Team builder system for discord

Author: Elcoyote Solitaire
"""
import asyncio
import discord

from discord import app_commands, Interaction
from discord.ext import commands
from cogs.intercogs import add_achievement


class Teambuilder(commands.Cog, name="teambuilder"):
    """
    Team building class

    Functions:
        edit_team()

    Commands:
        /build_team
        /join_team
        /switch_member
        /remove_team
        /print_teams
    """
    def __init__(self, bot):
        self.bot = bot
        self.teams = {}


    async def edit_team(self, guild: int, team_name: str):
        """
        Edits the message for a team.

        Automatically remove a team from self.teams if the
        message for the team list doesn't exist anymore

        Args:
            guild as interaction.guild.id
            team_name as str for the name of the team to edit it's message

        Returns:
            True if the message gets edited successfully
            False if the message failed to be edited
        """
        team = self.teams[guild].get(team_name)
        if not team:
            return False
        message = team.get("message")
        embed = discord.Embed(title=team_name, color=0xffffff)
        for role, slots in team["positions"].items():
            total_slots = len(slots)
            filled_slots = sum(1 for slot in slots if slot is not None)
            dash_count = len(role) + 5
            dashes = "-" * dash_count
            position_display = "\n".join(
                [f"{slot}" if slot is not None else dashes for slot in slots]
            )

            embed.add_field(
                name=f"**{role} ({filled_slots}/{total_slots})**",
                value=position_display,
                inline=True,
            )
        try:
            await message.edit(content="", embed=embed)
        except discord.NotFound:
            del self.teams[guild][team_name]
            return False
        return True


    @app_commands.command(
        name="build_team",
        description="Create the structure of the team"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        team_name="Name of the team (max 20 characters)",
        positions="What type of player and how many: [type1, amount] [type2, amount]"
    )
    async def build_team(self, interaction: Interaction, team_name: str, positions: str):
        """
        Create a team structure using type and amount

        The team structure is limited to:
            - MAX 20 characters for team name
            - MAX 9 positions
            - MAX 10 slots per position
            - MAX 75 total slots

        example:
            /build_team Whiskey Delta [range, 2] [melee, 4] [healer, 2] [scout, 1]

        Args:
            interaction as discord.Interaction
            team_name as str for the name of the team max 20 characters
            positions as str for the list of types and amount
        Uses:
            edit_team()
        """
        team_name = team_name.lower()
        if len(team_name) > 20:
            await interaction.response.send_message(
                content=f"Your team name is too long ({len(team_name)}/20)",
                ephemeral=True
            )
            return
        guild = interaction.guild.id

        if not hasattr(self, "teams"):
            self.teams = {}
        if guild not in self.teams:
            self.teams[guild] = {}
        if team_name not in self.teams[guild]:
            self.teams[guild][team_name] = {}
        else:
            await interaction.response.send_message(
                content=f"The name {team_name} already exists in the teams' list.",
                ephemeral=True
            )
            return

        team_positions = {}
        position_entries = positions.split("] [")
        position_entries[0] = position_entries[0][1:]
        position_entries[-1] = position_entries[-1][:-1]

        total_slots = 0

        for pos in position_entries:
            try:
                role, amount = pos.split(",")
                role = role.strip()
                amount = int(amount.strip())

                if role in team_positions:
                    await interaction.response.send_message(
                        content=f"Error: Duplicate role `{role}` in the command.",
                        ephemeral=True
                    )
                    return

                if amount > 10:
                    await interaction.response.send_message(
                        content=f"You are limited to 10 slots per role ({role}: {amount}/10.",
                        ephemeral=True
                    )
                    return

                team_positions[role] = [None] * amount
                total_slots += amount

            except ValueError:
                await interaction.response.send_message(
                    content="Error: Each position must be in the format `[type, amount]`, where "
                    "amount is an integer.",
                    ephemeral=True
                )
                return

        if len(team_positions) > 9:
            await interaction.response.send_message(
                content=f"The max limit of positions is 9. ({len(team_positions)}/9)",
                ephemeral=True
            )
            return

        if total_slots > 75:
            await interaction.response.send_message(
                content=f"The max limit of slots is 75 ({total_slots}/75).",
                ephemeral=True
            )
            return

        self.teams[guild][team_name]["positions"] = team_positions

        await interaction.response.send_message(
            content=f"Team __**{team_name}**__ created!",
            ephemeral=True
        )
        self.teams[guild][team_name]["channel"] = interaction.channel.id
        self.teams[guild][team_name]["message"] = await interaction.channel.send("Creating list")
        await asyncio.sleep(2)
        await self.edit_team(guild, team_name)


    @build_team.error
    async def build_team_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    async def teams_autocomplete(self, interaction: Interaction, current: str):
        """Provide autocomplete options based on team names."""
        guild = interaction.guild.id
        return [
            app_commands.Choice(name=team, value=team)
            for team in self.teams[guild] if current.lower() in team.lower()
        ]


    async def positions_autocomplete(self, interaction: Interaction, current: str):
        """Provide autocomplete options based on team names."""
        team_name = interaction.namespace.team_name
        guild = interaction.guild.id
        return [
            app_commands.Choice(name=position, value=position)
            for position in self.teams[guild][team_name]["positions"]
            if current.lower() in position.lower()
        ]


    async def members_autocomplete(self, interaction: Interaction, current: str):
        """Provide autocomplete options based on team names."""
        team_name = interaction.namespace.team_name
        guild = interaction.guild.id
        if team_name not in self.teams[guild]:
            return []

        members = []
        for _, slots in self.teams[guild][team_name]["positions"].items():
            members.extend(member for member in slots if member is not None)

        return [
            app_commands.Choice(name=member, value=member)
            for member in members
            if current.lower() in member.lower()
        ]


    async def new_positions_autocomplete(self, interaction: Interaction, current: str):
        """Provide autocomplete options based on team names."""
        team_name = interaction.namespace.new_team
        guild = interaction.guild.id
        return [
            app_commands.Choice(name=position, value=position)
            for position in self.teams[guild][team_name]["positions"]
            if current.lower() in position.lower()
        ]


    @app_commands.command(
        name="join_team",
        description="Join a position in a team"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        team_name="Name of the team to join",
        position="The position you want to join"
    )
    @app_commands.autocomplete(team_name=teams_autocomplete)
    @app_commands.autocomplete(position=positions_autocomplete)
    async def join_team(self, interaction: Interaction, team_name: str, position: str):
        """
        Join a position in a team

        Args:
            interaction as discord.Interaction
            team_name as autocompletion for team in self.teams
            position as autocompletion for position in team in self.teams

        Uses:
            edit_team()
        """
        guild = interaction.guild.id
        if team_name not in self.teams[guild]:
            await interaction.response.send_message(
                content=f"There's no team `{team_name}`",
                ephemeral=True
            )
            return
        if position not in self.teams[guild][team_name]["positions"]:
            await interaction.response.send_message(
                content=f"There's no position {position} in the team {team_name}.",
                ephemeral=True
            )
            return
        team = self.teams[guild][team_name]
        position_slots = team["positions"].get(position)
        for slots in team["positions"].values():
            if interaction.user.display_name in slots:
                await interaction.response.send_message(
                    content=f"You have already applied for a position in the team {team_name}.",
                    ephemeral=True
                )
                return
        if None not in position_slots:
            await interaction.response.send_message(
                content=f"Position `{position}` in team `{team_name}` is full.",
                ephemeral=True
            )
            return

        user_name = interaction.user.display_name
        position_slots[position_slots.index(None)] = user_name

        is_message = await self.edit_team(guild, team_name)
        if is_message:
            await interaction.response.send_message(
                content=f"You have successfully joined `{position}` in team `{team_name}`!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                content=f"The message for the list of the team {team_name} has been deleted. "
                "The team doesn't exist anymore.",
                ephemeral=True
            )


    @join_team.error
    async def join_team_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    @app_commands.command(
        name="switch_member",
        description="Switch a member to another team/position"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        team_name="Team where the member is",
        member="The member to move",
        new_team="The team where to send the member",
        new_position="The position where to place the member"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(team_name=teams_autocomplete)
    @app_commands.autocomplete(member=members_autocomplete)
    @app_commands.autocomplete(new_team=teams_autocomplete)
    @app_commands.autocomplete(new_position=new_positions_autocomplete)
    async def switch_member(
        self, interaction: Interaction, team_name: str,
        member: str, new_team: str, new_position: str
    ):
        """
        Takes a member from a team/position to move it to another team/position

        Args:
            interaction as discord.Interaction
            team_name as autocompletion for the team name where the member is
            position as autocompletion for the position where the member is
            member as autocompletion for the display name of the member to move
            new_team as autocompletion for the team where to send the member
            new_position as autocompletion for the position where to assign the member

        Uses:
            edit_team()
        """
        guild = interaction.guild.id
        source_team = self.teams[guild].get(team_name)
        if not source_team:
            await interaction.response.send_message(
                content=f"There is no team named {team_name}.",
                ephemeral=True
            )
            return

        member_found = False
        for _, slots in source_team["positions"].items():
            if member in slots:
                slots[slots.index(member)] = None
                member_found = True
                break

        if not member_found:
            await interaction.response.send_message(
                content=f"Member {member} is not part of {team_name} team.",
                ephemeral=True
            )
            return

        target_team = self.teams[guild].get(new_team)
        if not target_team:
            await interaction.response.send_message(
                content=f"Target team {new_team} does not exist.",
                ephemeral=True
            )
            return

        target_position = target_team["positions"].get(new_position)
        if not target_position:
            await interaction.response.send_message(
                content=f"Position {new_position} does not exist in team {new_team}.",
                ephemeral=True
            )
            return

        if None not in target_position:
            await interaction.response.send_message(
                content=f"Position {new_position} in team {new_team} is full.",
                ephemeral=True
            )
            return

        target_position[target_position.index(None)] = member

        await interaction.response.send_message(
            content=f"Member {member} has been moved from {team_name} to {new_team} in "
            f"position {new_position}.",
            ephemeral=True
        )

        await self.edit_team(guild, team_name)
        await self.edit_team(guild, new_team)


    @switch_member.error
    async def switch_member_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    @app_commands.command(
        name="remove_team",
        description="Remove the entire team from the list"
    )
    @app_commands.guild_only()
    @app_commands.describe(team_name="Team to remove from the list")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(team_name=teams_autocomplete)
    async def remove_team(self, interaction: Interaction, team_name: str):
        """
        Removes an entire team from the list of teams (self.teams)

        This command does NOT delete the message sent to list the team.

        Args:
            interaction as discord.Interaction
            team_name as str for the name of the team to remove
        """
        guild = interaction.guild.id
        team_to_remove = self.teams[guild].get(team_name)
        if not team_to_remove:
            await interaction.response.send_message(
                content=f"There is no team named {team_name}.",
                ephemeral=True
            )
            return
        del self.teams[guild][team_name]
        await interaction.response.send_message(
            content=f"The team {team_name} has been removed from the list.",
            ephemeral=True
        )


    @remove_team.error
    async def remove_team_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )


    @app_commands.command(
        name="print_teams",
        description="Dev command to see the nested dictionaries self.teams"
    )
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe()
    async def print_teams(self, interaction: Interaction):
        """
        Dev command to display the whole self.teams nested dictionaries
        """
        if len(str(self.teams)) > 1900:
            await interaction.response.send_message(
                content="The list is too long to be send in a message.",
                ephemeral=True
            )
            return
        await interaction.response.send_message(content=self.teams, ephemeral=True)


    @print_teams.error
    async def print_teams_error(self, interaction, error):
        """
        Returns any error as a reply to any command.
        """
        if isinstance(error, app_commands.errors.MissingPermissions):
            await add_achievement(interaction.guild.id, interaction.user.id, "Bold")
            await interaction.response.send_message(
                content="You don't have the permission to use this command.",
                ephemeral=True
            )
            return
        await add_achievement(interaction.guild.id, interaction.user.id, "Awkward")
        await interaction.response.send_message(
            content=f"An error occurred: {error}",
            ephemeral=True
        )



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Teambuilder(bot))
