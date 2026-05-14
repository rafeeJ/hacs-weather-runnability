"""Constants for the Best Run Time integration."""
from __future__ import annotations

DOMAIN = "best_run_time"

# Config keys
CONF_WEATHER_ENTITY = "weather_entity"
CONF_IDEAL_TEMP = "ideal_temp"
CONF_MAX_WIND = "max_wind"
CONF_MAX_RAIN_PROB = "max_rain_prob"
CONF_LOOK_AHEAD_HOURS = "look_ahead_hours"
CONF_RUN_WINDOW_START = "run_window_start_hour"
CONF_RUN_WINDOW_END = "run_window_end_hour"

# Defaults — tuned for road running in temperate climates
DEFAULT_IDEAL_TEMP = 12.0          # °C, sweet spot for most runners
DEFAULT_MAX_WIND = 30.0            # km/h above this is unpleasant
DEFAULT_MAX_RAIN_PROB = 30.0       # %
DEFAULT_LOOK_AHEAD_HOURS = 24
DEFAULT_RUN_WINDOW_START = 5       # only consider hours from 05:00...
DEFAULT_RUN_WINDOW_END = 22        # ...to 22:00 local time

UPDATE_INTERVAL_MINUTES = 30
