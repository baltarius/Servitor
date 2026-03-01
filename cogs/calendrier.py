# calendrier.py
"""
System to create an image with the calendar
of the selected month providing all special
days for that specific month.

Author: elcoyote solitaire
"""
import calendar
import os
import ephem
import holidays
import discord

from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo
from dateutil.easter import easter
from PIL import Image, ImageDraw, ImageFont
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands



class Calendrier(commands.Cog, name="calendrier"):
    """
    Class calendrier for generating calenders with
    the special days of the selected year/month.

    This class contains commands, functions,
    and tools used to create an image of a
    calendar with the special days of the month

    Functions:
        get_calendar_data()
        render_calendar_image()
        get_dst_transitions()
        get_recurring_observances()
        get_public_holidays()
        get_easter_related()
        get_astronomical_events()
        merge_event_dicts()
        get_all_special_dates()

    Commands:
        /calendar
    """
    def __init__(self, bot):
        self.bot = bot



    async def get_calendar_data(self, year: int, month: int):
        """
        Get the data/matrix for the calendar

        Args:
            year as int for the year
            month as int for the month (1~12)

        Used by:
            get_all_special_dates()

        Returns:
             data as dict for the month's matrix
        """
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(year, month)
        return {
            "year": year,
            "month": month,
            "matrix": month_days
        }


    async def render_calendar_image(self, data, specials):
        """
        Generates a calendar from set of data

        Used by:
            get_all_special_dates()

        Args:
            data as dict for the year, month, and matrix for the days
            specials as dict for the special events of the month
        """
        width = 1000
        height = 1000
        footer_start_y = 720
        cell_w = width // 7
        cell_h = 90
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)
        try:
            title_font = ImageFont.truetype("arial.ttf", 40)
            day_font = ImageFont.truetype("arial.ttf", 28)
            event_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            day_font = ImageFont.load_default()
            event_font = ImageFont.load_default()
        title = f"{calendar.month_name[data['month']]} {data['year']}"
        draw.text((width // 2, 30), title, fill="black", anchor="mm", font=title_font)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            draw.text(
                (i * cell_w + cell_w // 2, 100),
                day,
                fill="black",
                anchor="mm",
                font=day_font
            )
        start_y = 140
        for row_idx, week in enumerate(data["matrix"]):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue
                center_x = col_idx * cell_w + cell_w // 2
                center_y = start_y + row_idx * cell_h + cell_h // 2
                color = "red" if day in specials else "black"
                draw.text(
                    (center_x, center_y),
                    str(day),
                    fill=color,
                    font=day_font,
                    anchor="mm"
                )
        draw.line((50, footer_start_y - 20, width - 50, footer_start_y - 20), fill="black", width=2)
        y_text = footer_start_y
        line_spacing = 32
        sorted_days = sorted(specials.keys())
        if sorted_days:
            for day in sorted_days:
                events = specials[day].split(" | ")
                for event in events:
                    event_text = f"{day}: {event}"
                    draw.text((50, y_text), event_text, fill="black", font=event_font)
                    y_text += line_spacing
        else:
            draw.text((80, y_text), "No special events this month.",
                      fill="gray", font=event_font)
        filename = f"{data['year']}_{data['month']:02d}_calendar.png"
        os.makedirs("./calendar", exist_ok=True)
        filepath = os.path.join("./calendar", filename)
        img.save(filepath, format="PNG")
        return filepath


    async def get_dst_transitions(self, year, month, tz_name):
        """
        Verify for daytime saving days (start/end)

        Used by:
            get_all_special_dates()

        Args:
            year as int for the year
            month as int for the month (1~12)
            tz_name as str for the timezone ("America/Montreal" used)

        Returns:
            transitions as dict for daytime saving days
        """
        timez = ZoneInfo(tz_name)
        transitions = {}
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            day1 = datetime(year, month, day, 12, tzinfo=timez)
            day2 = day1 + timedelta(days=1)
            if day1.dst() != day2.dst():
                if day2.dst() > day1.dst():
                    transitions[day + 1] = "Daylight Saving Time Starts"
                else:
                    transitions[day + 1] = "Daylight Saving Time Ends"
        return transitions


    async def get_recurring_observances(self, month):
        """
        List of recurring days through the years

        Args:
            month as int for the month (1~12)

        Used by:
            get_all_special_dates()

        Returns:
             events as dict for the static events of the year
        """
        events = {}
        fixed = [
            (2, 14, "Valentine's Day"),
            (3, 8, "International Women's Day"),
            (3, 17, "St. Patrick's Day"),
            (4, 22, "Earth Day"),
            (5, 1, "International Workers' Day"),
            (10, 31, "Halloween"),
            (11, 11, "Remembrance Day"),
            (12, 24, "Christmas Eve"),
            (12, 31, "New Year's Eve"),
        ]
        for monthz, day, name in fixed:
            if monthz == month:
                events[day] = name
        return events


    async def get_public_holidays(self, year, month, country, subdiv=None):
        """
        Generates a dictionary of holidays for the country

        The dictionary combines the country's holidays and the
        subdivision's holidays if any subdivision is specified

        Args:
            year as int for the year
            month as int for the month (1~12)
            country as str for the initial of the country (CA, USA, FR)
            subdiv as str for the state/province/sub area

        Used by:
            get_all_special_dates()

        Returns:
            public as dict for the public holidays of the year/month
        """
        country_h = holidays.country_holidays(country, years=year, observed=True)
        subdiv_h = {}
        if subdiv:
            subdiv_h = holidays.country_holidays(
                country,
                subdiv=subdiv,
                years=year
            )
        merged = {}
        for day, name in country_h.items():
            if day.month == month:
                merged[day] = name
        for day, name in subdiv_h.items():
            if day.month == month:
                if day in merged:
                    if name not in merged[day]:
                        merged[day] += f" | {name}"
                else:
                    merged[day] = name
        return {day.day: name for day, name in merged.items()}


    async def get_easter_related(self, year, month):
        """
        Checks for Easter dates with the year/month

        Args:
            year as int for the year
            month as int for the month (1~12)

        Used by:
            get_all_special_dates()

        Returns:
            events as dict for the Easter related day of the year/month
        """
        events = {}
        easter_sunday = easter(year)
        good_friday = easter_sunday - timedelta(days=2)
        easter_monday = easter_sunday + timedelta(days=1)
        candidates = [
            (good_friday, "Good Friday"),
            (easter_sunday, "Easter Sunday"),
            (easter_monday, "Easter Monday"),
        ]
        for day, name in candidates:
            if day.month == month:
                events[day.day] = name
        return events


    async def get_astronomical_events(self, year, month):
        """
        Generates the days for the Equinoxes and Solstices of the year/month

        Args:
            year as int for the year
            month as int for the month (1~12)

        Used by:
            get_all_special_dates()

        Returns:
            events as dict for the astral events of the year/month
        """
        events = {}
        spring = ephem.next_vernal_equinox(f"{year}/1/1")
        spring_date = ephem.Date(spring).datetime().date()
        summer = ephem.next_summer_solstice(f"{year}/1/1")
        summer_date = ephem.Date(summer).datetime().date()
        autumn = ephem.next_autumnal_equinox(f"{year}/1/1")
        autumn_date = ephem.Date(autumn).datetime().date()
        winter = ephem.next_winter_solstice(f"{year}/1/1")
        winter_date = ephem.Date(winter).datetime().date()
        for day, name in [
            (spring_date, "Spring Equinox"),
            (summer_date, "Summer Solstice"),
            (autumn_date, "Autumn Equinox"),
            (winter_date, "Winter Solstice"),
        ]:
            if day.year == year and day.month == month:
                events[day.day] = name
        return events


    async def merge_event_dicts(self, *dicts):
        """
        Safely merge all dictionaries for the special dates

        Args:
            dicts as *arg for the name of the dictionaries to merge

        Used by:
            get_all_special_dates()

        Returns:
             final as dict for the sorted, duplicateless special days of the year/month
        """
        merged = {}
        for dayz in dicts:
            for day, name in dayz.items():
                if day not in merged:
                    merged[day] = set()
                merged[day].add(name)
        final = {}
        for day in sorted(merged):
            final[day] = " | ".join(sorted(merged[day]))
        return final


    async def get_all_special_dates(self, year, month, country, subdiv=None, timez=None):
        """
        Master function to call all other functions to generate a complete
        calendar with the text of all the special days of the month

        Args:
            year as int for the year
            month as int for the month (1~12)
            country as str for the initial of the country (CA, US, FR)
            subdiv as str for state/province/sub area
            timez as str for timezone

        Returns:
            image_path as str for the filepath of the image
        """
        data = await self.get_calendar_data(year, month)
        public = await self.get_public_holidays(year, month, country, subdiv)
        astro = await self.get_astronomical_events(year, month)
        dst = await self.get_dst_transitions(year, month, timez) if timez else {}
        recurring = await self.get_recurring_observances(month)
        easterz = await self.get_easter_related(year, month)
        merged_events =  await self.merge_event_dicts(public, astro, dst, recurring, easterz)
        image_path = await self.render_calendar_image(data, merged_events)
        return image_path


    LOCATION_DATA = {
        "Canada": {
            "code": "CA",
             "subareas": {
                "New Brunswick": {"code": "NB", "tz": "America/Moncton"},
                "Nova Scotia": {"code": "NS", "tz": "America/Halifax"},
                "Prince Edward Island": {"code": "PE", "tz": "America/Halifax"},
                "Newfoundland and Labrador": {"code": "NL", "tz": "America/St_Johns"},
                "Quebec": {"code": "QC", "tz": "America/Montreal"},
                "Ontario": {"code": "ON", "tz": "America/Toronto"},
                "Manitoba": {"code": "MB", "tz": "America/Winnipeg"},
                "Saskatchewan": {"code": "SK", "tz": "America/Regina"},
                "Alberta": {"code": "AB", "tz": "America/Edmonton"},
                "British Columbia": {"code": "BC", "tz": "America/Vancouver"},
                "Yukon": {"code": "YT", "tz": "America/Whitehorse"},
                "Northwest Territories": {"code": "NT", "tz": "America/Yellowknife"},
                "Nunavut": {"code": "NU", "tz": "America/Iqaluit"},
            }
        },
        "United States": {
            "code": "US",
            "subareas": {
                "Alabama": {"code": "AL", "tz": "America/Chicago"},
                "Alaska": {"code": "AK", "tz": "America/Anchorage"},
                "Arizona": {"code": "AZ", "tz": "America/Phoenix"},
                "Arkansas": {"code": "AR", "tz": "America/Chicago"},
                "California": {"code": "CA", "tz": "America/Los_Angeles"},
                "Colorado": {"code": "CO", "tz": "America/Denver"},
                "Connecticut": {"code": "CT", "tz": "America/New_York"},
                "Delaware": {"code": "DE", "tz": "America/New_York"},
                "Florida": {"code": "FL", "tz": "America/New_York"},
                "Georgia": {"code": "GA", "tz": "America/New_York"},
                "Hawaii": {"code": "HI", "tz": "Pacific/Honolulu"},
                "Idaho": {"code": "ID", "tz": "America/Boise"},
                "Illinois": {"code": "IL", "tz": "America/Chicago"},
                "Indiana": {"code": "IN", "tz": "America/Indiana/Indianapolis"},
                "Iowa": {"code": "IA", "tz": "America/Chicago"},
                "Kansas": {"code": "KS", "tz": "America/Chicago"},
                "Kentucky": {"code": "KY", "tz": "America/New_York"},
                "Louisiana": {"code": "LA", "tz": "America/Chicago"},
                "Maine": {"code": "ME", "tz": "America/New_York"},
                "Maryland": {"code": "MD", "tz": "America/New_York"},
                "Massachusetts": {"code": "MA", "tz": "America/New_York"},
                "Michigan": {"code": "MI", "tz": "America/New_York"},
                "Minnesota": {"code": "MN", "tz": "America/Chicago"},
                "Mississippi": {"code": "MS", "tz": "America/Chicago"},
                "Missouri": {"code": "MO", "tz": "America/Chicago"},
                "Montana": {"code": "MT", "tz": "America/Denver"},
                "Nebraska": {"code": "NE", "tz": "America/Chicago"},
                "Nevada": {"code": "NV", "tz": "America/Los_Angeles"},
                "New Hampshire": {"code": "NH", "tz": "America/New_York"},
                "New Jersey": {"code": "NJ", "tz": "America/New_York"},
                "New Mexico": {"code": "NM", "tz": "America/Denver"},
                "New York": {"code": "NY", "tz": "America/New_York"},
                "North Carolina": {"code": "NC", "tz": "America/New_York"},
                "North Dakota": {"code": "ND", "tz": "America/Chicago"},
                "Ohio": {"code": "OH", "tz": "America/New_York"},
                "Oklahoma": {"code": "OK", "tz": "America/Chicago"},
                "Oregon": {"code": "OR", "tz": "America/Los_Angeles"},
                "Pennsylvania": {"code": "PA", "tz": "America/New_York"},
                "Rhode Island": {"code": "RI", "tz": "America/New_York"},
                "South Carolina": {"code": "SC", "tz": "America/New_York"},
                "South Dakota": {"code": "SD", "tz": "America/Chicago"},
                "Tennessee": {"code": "TN", "tz": "America/Chicago"},
                "Texas": {"code": "TX", "tz": "America/Chicago"},
                "Utah": {"code": "UT", "tz": "America/Denver"},
                "Vermont": {"code": "VT", "tz": "America/New_York"},
                "Virginia": {"code": "VA", "tz": "America/New_York"},
                "Washington": {"code": "WA", "tz": "America/Los_Angeles"},
                "West Virginia": {"code": "WV", "tz": "America/New_York"},
                "Wisconsin": {"code": "WI", "tz": "America/Chicago"},
                "Wyoming": {"code": "WY", "tz": "America/Denver"},
            }
        },
        "France": {
            "code": "FR",
            "subareas": {
                "Metropolitan France": {
                    "code": None,
                    "tz": "Europe/Paris"
                }
            }
        }
    }


    async def year_autocomplete(
        self, interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocompletion for the year
        """
        now = datetime.now().year
        years = [now -1, now, now + 1]
        return [
            app_commands.Choice(name=str(year), value=year)
            for year in years if current in str(year)
        ]


    async def country_autocomplete(
        self, interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocompletion for the country
        """
        return [
            app_commands.Choice(name=country, value=country)
            for country in self.LOCATION_DATA.keys()
            if current.lower() in country.lower()
        ]


    async def subarea_autocomplete(
        self, interaction: Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """
        Autocompletion for the subarea
        """
        country = interaction.namespace.country
        if not country or country not in self.LOCATION_DATA:
            return []
        subareas = self.LOCATION_DATA[country]["subareas"]
        return [
            app_commands.Choice(name=name, value=name)
            for name in subareas
            if current.lower() in name.lower()
        ][:20]


    @app_commands.command(
        name="calendar",
        description="Shows a calendar of the specified month with the special days"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.checks.cooldown(2, 300.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(
        year="The year",
        month="The month",
        country="The country",
        subarea="The sub area",
        perso="For you or public"
    )
    @app_commands.choices(month=[
        Choice(name="January", value=1),
        Choice(name="February", value=2),
        Choice(name="March", value=3),
        Choice(name="April", value=4),
        Choice(name="May", value=5),
        Choice(name="June", value=6),
        Choice(name="July", value=7),
        Choice(name="August", value=8),
        Choice(name="September", value=9),
        Choice(name="October", value=10),
        Choice(name="November", value=11),
        Choice(name="December", value=12)
    ])
    @app_commands.choices(perso=[
        Choice(name="perso", value=1),
        Choice(name="public", value=2)
    ])
    @app_commands.autocomplete(
        year=year_autocomplete,
        country=country_autocomplete,
        subarea=subarea_autocomplete
    )
    async def calendar(
        self, interaction: Interaction,
        year: int, month: Choice[int],
        country: str, subarea: str = None,
        perso: Choice[int] = None
    ):
        """
        Generates a calender to send it to the user

        Args:
            interaction as discord.Interaction
            year as int for the year, choice between previous/current/next year
            month as int for the month (1~12)
            country as str for the name of the country to fetch special days
            subarea as str for area specific days (states/provinces) (optional)
            perso as str for choice between a private response (ephemeral) or public
        """
        if country not in self.LOCATION_DATA:
            await interaction.response.send_message(
                "Invalid country.", ephemeral=True
            )
            return
        ephemeral1 = (perso.value if perso else 1) == 1
        await interaction.response.send_message(
            content="Generating the calendar, please wait . . .",
            ephemeral=ephemeral1
        )
        country_code = self.LOCATION_DATA[country]["code"]
        timez = None
        subdiv_code = None
        if subarea:
            sub_data = self.LOCATION_DATA[country]["subareas"].get(subarea)
            if not sub_data:
                await interaction.response.send_message(
                    "Invalid subarea.", ephemeral=True
                )
                return
            subdiv_code = sub_data["code"]
            timez = sub_data["tz"]
        filepath = (
            await self.get_all_special_dates(
                int(year), int(month.value), country_code, subdiv_code, timez
            )
        )
        if filepath:
            calendar_img = discord.File(filepath)
            await interaction.edit_original_response(
                content=f"{month.name} {year} calendar for {country} ({subarea})",
                attachments=[calendar_img]
            )
            return
        await interaction.edit_original_response(content="Something went wrong!")



async def setup(bot):
    """
    Loads the cog on start.
    """
    await bot.add_cog(Calendrier(bot))
