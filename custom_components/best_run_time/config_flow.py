"""Config flow for the Best Run Time integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

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
)


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for the tuneable scoring options."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_IDEAL_TEMP,
                default=defaults.get(CONF_IDEAL_TEMP, DEFAULT_IDEAL_TEMP),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_MAX_WIND,
                default=defaults.get(CONF_MAX_WIND, DEFAULT_MAX_WIND),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_MAX_RAIN_PROB,
                default=defaults.get(CONF_MAX_RAIN_PROB, DEFAULT_MAX_RAIN_PROB),
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Optional(
                CONF_LOOK_AHEAD_HOURS,
                default=defaults.get(CONF_LOOK_AHEAD_HOURS, DEFAULT_LOOK_AHEAD_HOURS),
            ): vol.All(int, vol.Range(min=1, max=120)),
            vol.Optional(
                CONF_RUN_WINDOW_START,
                default=defaults.get(CONF_RUN_WINDOW_START, DEFAULT_RUN_WINDOW_START),
            ): vol.All(int, vol.Range(min=0, max=23)),
            vol.Optional(
                CONF_RUN_WINDOW_END,
                default=defaults.get(CONF_RUN_WINDOW_END, DEFAULT_RUN_WINDOW_END),
            ): vol.All(int, vol.Range(min=0, max=23)),
        }
    )


class BestRunTimeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            entity_id = user_input[CONF_WEATHER_ENTITY]
            await self.async_set_unique_id(entity_id)
            self._abort_if_unique_id_configured()
            if user_input[CONF_RUN_WINDOW_START] >= user_input[CONF_RUN_WINDOW_END]:
                errors["base"] = "invalid_window"
            else:
                return self.async_create_entry(
                    title=f"Best Run Time ({entity_id})",
                    data={CONF_WEATHER_ENTITY: entity_id},
                    options={
                        k: v
                        for k, v in user_input.items()
                        if k != CONF_WEATHER_ENTITY
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_WEATHER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
            }
        ).extend(_options_schema(user_input or {}).schema)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return BestRunTimeOptionsFlow(entry)


class BestRunTimeOptionsFlow(OptionsFlow):
    """Allow editing the scoring parameters after install."""

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_RUN_WINDOW_START] >= user_input[CONF_RUN_WINDOW_END]:
                errors["base"] = "invalid_window"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.entry.options),
            errors=errors,
        )
