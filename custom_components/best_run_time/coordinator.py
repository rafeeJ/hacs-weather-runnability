"""Coordinator that pulls hourly forecast and scores each hour."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_IDEAL_TEMP,
    CONF_LOOK_AHEAD_HOURS,
    CONF_MAX_RAIN_PROB,
    CONF_MAX_WIND,
    CONF_RUN_WINDOW_END,
    CONF_RUN_WINDOW_START,
    CONF_WEATHER_ENTITY,
    DEFAULT_IDEAL_TEMP,
    DEFAULT_LOOK_AHEAD_HOURS,
    DEFAULT_MAX_RAIN_PROB,
    DEFAULT_MAX_WIND,
    DEFAULT_RUN_WINDOW_END,
    DEFAULT_RUN_WINDOW_START,
    DOMAIN,
    UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


class BestRunTimeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches the hourly forecast and scores it."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.entry = entry
        # data holds the entity choice; options hold the tuneable scoring params.
        self.weather_entity: str = entry.data[CONF_WEATHER_ENTITY]
        opts = {**entry.data, **(entry.options or {})}
        self.ideal_temp: float = opts.get(CONF_IDEAL_TEMP, DEFAULT_IDEAL_TEMP)
        self.max_wind: float = opts.get(CONF_MAX_WIND, DEFAULT_MAX_WIND)
        self.max_rain: float = opts.get(CONF_MAX_RAIN_PROB, DEFAULT_MAX_RAIN_PROB)
        self.look_ahead: int = opts.get(CONF_LOOK_AHEAD_HOURS, DEFAULT_LOOK_AHEAD_HOURS)
        self.window_start: int = opts.get(CONF_RUN_WINDOW_START, DEFAULT_RUN_WINDOW_START)
        self.window_end: int = opts.get(CONF_RUN_WINDOW_END, DEFAULT_RUN_WINDOW_END)

    async def _async_update_data(self) -> dict[str, Any]:
        """Pull the forecast and produce a scored result."""
        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": self.weather_entity, "type": "hourly"},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:
            raise UpdateFailed(f"weather.get_forecasts failed: {err}") from err

        forecast = (
            (response or {}).get(self.weather_entity, {}).get("forecast", [])
        )
        if not forecast:
            raise UpdateFailed(
                f"No hourly forecast returned from {self.weather_entity}. "
                "Does this weather entity expose an hourly forecast?"
            )

        now = dt_util.utcnow()
        cutoff = now + timedelta(hours=self.look_ahead)
        scored: list[dict[str, Any]] = []

        for hour in forecast:
            dt_str = hour.get("datetime")
            if not dt_str:
                continue
            dt_obj = dt_util.parse_datetime(dt_str)
            if dt_obj is None:
                continue
            if dt_obj < now or dt_obj > cutoff:
                continue

            # Filter by local-time run window (e.g. don't run at 3am)
            local_hour = dt_util.as_local(dt_obj).hour
            if not (self.window_start <= local_hour <= self.window_end):
                continue

            score, reasons = self._score_hour(hour)
            scored.append(
                {
                    "datetime": dt_obj.isoformat(),
                    "local_time": dt_util.as_local(dt_obj).strftime("%a %H:%M"),
                    "score": round(score, 1),
                    "temperature": hour.get("temperature"),
                    "precipitation_probability": hour.get("precipitation_probability"),
                    "wind_speed": hour.get("wind_speed"),
                    "humidity": hour.get("humidity"),
                    "condition": hour.get("condition"),
                    "reasons": reasons,
                }
            )

        if not scored:
            raise UpdateFailed(
                "No forecast hours fell within the look-ahead window and "
                "run-window hours. Try widening the window in the options."
            )

        scored.sort(key=lambda h: h["score"], reverse=True)
        return {
            "best": scored[0],
            "top_3": scored[:3],
            "all": scored,
        }

    def _score_hour(self, hour: dict[str, Any]) -> tuple[float, list[str]]:
        """Compute a 0..100-ish runnability score plus negative reasons."""
        score = 100.0
        reasons: list[str] = []

        # Temperature: quadratic-ish penalty around the ideal
        temp = hour.get("temperature")
        if temp is not None:
            delta = abs(temp - self.ideal_temp)
            score -= delta * 2.5
            if temp > 25:
                score -= (temp - 25) * 3  # extra penalty when hot
                reasons.append(f"hot ({temp}°C)")
            elif temp < 0:
                score -= abs(temp) * 2
                reasons.append(f"freezing ({temp}°C)")

        # Rain probability
        rain = hour.get("precipitation_probability")
        if rain is not None:
            score -= rain * 0.5
            if rain >= self.max_rain:
                score -= 15
                reasons.append(f"rain likely ({rain}%)")

        # Wind speed
        wind = hour.get("wind_speed")
        if wind is not None:
            score -= wind * 0.4
            if wind >= self.max_wind:
                score -= 10
                reasons.append(f"windy ({wind} km/h)")

        # Humidity (matters more at higher temps)
        humidity = hour.get("humidity")
        if humidity is not None and humidity > 80:
            penalty = (humidity - 80) * 0.3
            if temp is not None and temp > 20:
                penalty *= 1.5
            score -= penalty
            reasons.append(f"humid ({humidity}%)")

        # Adverse conditions
        condition = (hour.get("condition") or "").lower()
        if condition in {"lightning", "lightning-rainy", "hail"}:
            score -= 40
            reasons.append(f"severe weather: {condition}")
        elif condition in {"snowy", "snowy-rainy"}:
            score -= 15
            reasons.append("snow")
        elif condition == "fog":
            score -= 5
            reasons.append("fog")

        return max(score, 0.0), reasons
