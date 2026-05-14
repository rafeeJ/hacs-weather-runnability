# Best Run Time

A Home Assistant custom integration that figures out the best upcoming hour to go for a run based on the weather forecast. It pulls hourly forecast data from any existing weather entity (Met.no, OpenWeatherMap, Pirate Weather, AccuWeather, etc.), scores each hour on temperature, rain probability, wind, humidity, and conditions, and exposes two sensors:

- `sensor.best_run_time` — a timestamp of the highest-scoring upcoming hour
- `sensor.best_run_score` — the numeric runnability score for that hour

Both sensors expose attributes including the top 3 windows and the temperature/wind/rain values for the best hour, so you can build cards or automations off them.

## Installation

### Via HACS (recommended)

1. In HACS, go to **Integrations** → **⋮** → **Custom repositories**.
2. Add this repo URL and select category **Integration**.
3. Search for "Best Run Time" in HACS and install.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration** and search for **Best Run Time**.

### Manual install

Copy `custom_components/best_run_time` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

All configuration is done in the UI. You'll be asked for:

| Field | Default | Notes |
|---|---|---|
| Weather entity | — | Any `weather.*` entity that supports hourly forecasts |
| Ideal temperature (°C) | 12 | Sweet spot for the temperature penalty curve |
| Max acceptable wind (km/h) | 30 | Anything above gets an extra penalty |
| Max acceptable rain probability (%) | 30 | Anything above gets an extra penalty |
| Look-ahead hours | 24 | How far into the future to consider |
| Earliest run hour | 5 | Local-time filter (don't recommend 3am) |
| Latest run hour | 22 | Local-time filter |

These can all be edited later via **Configure** on the integration.

## How the score works

Each forecast hour starts at 100 points and gets penalties subtracted for:

- Distance from ideal temperature (linear penalty, extra penalty above 25°C or below 0°C)
- Rain probability (0.5 pts per %)
- Wind speed (0.4 pts per km/h)
- High humidity (above 80%, weighted up when also hot)
- Severe conditions (lightning, hail, snow, fog)

The highest-scoring hour wins. Tune the constants in `coordinator.py` if your preferences differ.

## Example automation

```yaml
automation:
  - alias: "Notify me about the best run window"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: notify.mobile_app_yourphone
        data:
          title: "Best run time today"
          message: >
            {{ as_timestamp(states('sensor.best_run_time')) | timestamp_custom('%H:%M') }}
            — score {{ states('sensor.best_run_score') }}.
            Top 3: {{ state_attr('sensor.best_run_time', 'top_3') |
                      map(attribute='local_time') | join(', ') }}.
```

## Requirements

- Home Assistant 2024.6.0 or later
- A weather integration whose entity supports the `weather.get_forecasts` service with `type: hourly`

## License

MIT
