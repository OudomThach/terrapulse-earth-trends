"""Catalog of Earth-system variables: plain-language names, units, and meaning.

Every variable is a monthly record from satellite-driven reanalysis, 1990-2025.
Definitions are written for students and curious non-specialists.
"""

from __future__ import annotations

from dataclasses import dataclass

GROUPS = ["Temperature", "Water cycle", "Land & soil", "Sun & energy", "Air & atmosphere"]


@dataclass(frozen=True)
class Variable:
    """One Earth-system variable: code, plain-language name, unit, group and meaning."""

    code: str
    name: str
    unit: str
    group: str
    definition: str
    rising_means: str
    decimals: int = 2
    since: int | None = None  # first year with data, if later than 1990


VARIABLES: dict[str, Variable] = {v.code: v for v in [
    # ---- Temperature
    Variable("T2M", "Air temperature", "°C", "Temperature",
             "Average air temperature measured 2 metres above the ground.",
             "The air near the surface is getting warmer."),
    Variable("T2M_MAX", "Daytime high", "°C", "Temperature",
             "The average of each day's warmest reading.",
             "Hot afternoons are getting hotter."),
    Variable("T2M_MIN", "Night-time low", "°C", "Temperature",
             "The average of each day's coolest reading.",
             "Nights are cooling off less than they used to."),
    Variable("TS", "Surface temperature", "°C", "Temperature",
             "The 'skin' temperature of the ground, ice or sea surface itself, not the air above it.",
             "The surface itself is warming."),
    Variable("FROST_DAYS", "Frost days", "days/month", "Temperature",
             "How many days per month dip below freezing (0 °C).",
             "More freezing days; the place is getting colder."),
    # ---- Water cycle
    Variable("PRECTOTCORR", "Precipitation", "mm/day", "Water cycle",
             "Rain and snow (as water) reaching the ground, averaged per day.",
             "It is getting wetter."),
    Variable("RH2M", "Relative humidity", "%", "Water cycle",
             "How full of water vapour the air is, compared with the most it could hold at that temperature.",
             "The air is closer to saturated."),
    Variable("QV2M", "Specific humidity", "g/kg", "Water cycle",
             "Grams of water vapour in each kilogram of air. Warmer air can hold more.",
             "The air holds more moisture in absolute terms."),
    Variable("TQV", "Water vapour in the sky", "kg/m²", "Water cycle",
             "All the water vapour in a column of air from the ground to space (equal to millimetres of water).",
             "More water vapour sits above the place."),
    Variable("EVLAND", "Evaporation from land", "mm/day", "Water cycle",
             "Water returning to the air from soil, plants and lakes.",
             "The land is losing water to the air faster.", decimals=3),
    # ---- Land & soil
    Variable("GWETROOT", "Root-zone soil wetness", "0-1", "Land & soil",
             "How full of water the soil is where plant roots reach (0 = bone dry, 1 = saturated).",
             "Soil is wetter.", decimals=3),
    Variable("GWETTOP", "Surface soil wetness", "0-1", "Land & soil",
             "How wet the top few centimetres of soil are (0 = dry, 1 = saturated).",
             "The soil surface is wetter.", decimals=3),
    Variable("SNODP", "Snow depth", "cm", "Land & soil",
             "Average depth of snow on the ground.",
             "More snow cover."),
    # ---- Sun & energy
    Variable("ALLSKY_SFC_SW_DWN", "Sunlight at the ground", "kWh/m²/day", "Sun & energy",
             "Solar energy that actually reaches the surface after clouds and haze take their share.",
             "More sunshine arrives at the surface.", decimals=3),
    Variable("ALLSKY_SFC_LW_DWN", "Heat glow from the sky", "kWh/m²/day", "Sun & energy",
             "Invisible infrared heat radiated down by the atmosphere. Greenhouse gases, water vapour and clouds raise it.",
             "The atmosphere is sending more heat back down.", decimals=3),
    Variable("CLOUD_AMT", "Cloud cover", "%", "Sun & energy",
             "Share of the sky covered by cloud.",
             "Skies are cloudier."),
    # ---- Air & atmosphere
    Variable("PS", "Surface air pressure", "kPa", "Air & atmosphere",
             "The weight of the air column pressing on the ground.",
             "Air pressure is higher on average.", decimals=3),
    Variable("WS10M", "Wind speed", "m/s", "Air & atmosphere",
             "Average wind speed 10 metres above the ground.",
             "It is windier."),
    Variable("TO3", "Ozone layer thickness", "Dobson units", "Air & atmosphere",
             "Total ozone in the air column above the place. Ozone shields the ground from ultraviolet light.",
             "A thicker ozone layer.", decimals=1),
    Variable("AOD_55", "Aerosol haze", "index", "Air & atmosphere",
             "How much dust, smoke and pollution particles dim the sunlight (aerosol optical depth). Record starts in 2000.",
             "The air is hazier.", decimals=3, since=2000),
]}

CODES = list(VARIABLES)
assert len(CODES) <= 20, "the data service allows at most 20 parameters per request"
