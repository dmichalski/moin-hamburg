# Moin Hamburg

**English** · [Deutsch](README.de.md)

A living Hamburg skyline for Home Assistant: a drawn harbour panorama as your
dashboard background that follows the weather, the wind, the season, the moon,
storm warnings and Hamburg's special days -- the Dom's Ferris wheel in autumn,
tall ships for the harbour birthday, lanterns on St. Martin, fireworks at New
Year's Eve.

![The skyline through the year: summer, the harbour birthday, rain, a storm
warning, the Dom, St Martin, snow, Christmas, New Year's Eve, cherry blossom
fireworks, Pride and a hot evening](https://dmichalski.github.io/moin-hamburg/showcase.gif)

**[Try every picture in your browser](https://dmichalski.github.io/moin-hamburg/)**
-- the real generator, running on the page.

## What the picture shows

| | from |
|---|---|
| Day, dusk, night | the sun's elevation (above 6°, down to -6°, below) |
| Clear, cloudy, rain, snow | now and the next three forecast hours |
| Calm, windy, storm; wind from east or west | gusts now and in the next three hours (40 and 75 km/h) |
| Spring, summer, autumn, winter | the month |
| Moon phase | computed, as Home Assistant's moon sensor has it |
| The tide: the Elbe falls and bares the quay wall | the gauge Hamburg St. Pauli, in five steps from mean low to mean high tide |
| Heat, cold, fog, thunder, snow cover, storm surge | temperatures, forecast, warnings; snow cover after two hours of snow at 1 °C or less, gone after six hours above 3 °C; a storm surge also from the gauge, 1.5 m above mean high tide |
| Ice drift: pack ice on the Elbe, ice along the quay | four days of frost without a reading above 0 °C; gone after two days without frost |
| Storm balls on the signal mast | storm and hurricane warnings |
| Special days | the date, your calendars, the bin collection |

Only one special day is drawn at a time, the most important: a quiet day
(Good Friday, the days of remembrance in November) wins over everything and
keeps the picture calm, then a birthday, then single days, then periods (Dom,
school holidays, Advent), then the bin lorry.

| Special day | when |
|---|---|
| New Year's Eve, New Year's Day | 31 December from 18:00 to 1 January 2:00; then until noon |
| Epiphany, Valentine's Day, Carnival, Easter, Ascension Day, Mother's Day, Halloween, St Martin's Day, St Nicholas' Day, Christmas, clock change, quiet days, Advent | computed from the date |
| Summer solstice | 20 to 22 June |
| Shooting stars | 10 to 14 August and 12 to 15 December, after sunset |
| First snow | the day it first snows for 15 minutes, October to April |
| Birthday, harbour birthday, cherry blossom festival, Pride (CSD), Blue Port, Dom, school holidays | your calendars, by keyword |
| Bin day | any event in a bin collection calendar today, from 6 to 10 in the morning |

Birthday names never appear in the picture, only in the greeting.

## Installation

[![Open the repository in your Home Assistant](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dmichalski&repository=moin-hamburg&category=integration)

* Home Assistant 2026.11 or newer: *Settings → Marketplace → Add from link*,
  enter `dmichalski/moin-hamburg`, then download it.
* Home Assistant 2026.9 and 2026.10: in HACS, *Custom repositories*, add the
  repository as an *Integration*, then download it.
* By hand: copy `custom_components/moin_hamburg` into your configuration folder.

Then restart Home Assistant.

The integration writes its themes to `themes/moin-hamburg.yaml`. Home Assistant
loads themes from there if `configuration.yaml` has

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

If it doesn't, the integration raises a repair issue that says so.

## Setup

*Settings → Devices & services → Add integration → Moin Hamburg.*

| Field | |
|---|---|
| Weather | required; a weather entity with an hourly forecast (Met.no, DWD, ...) |
| Weather warnings | optional; NINA warning binary sensors or their headline sensors, or DWD warning level sensors |
| Calendars with Hamburg events, birthdays and school holidays | optional; events count by title |
| Bin collection calendars | optional; any event on a day means collection day |
| Water level at Hamburg St. Pauli | optional; the water level sensor of the gauge "HAMBURG ST. PAULI" |
| Make Moin Hamburg the default theme | for all users and devices; otherwise choose the theme in your profile |

The options add the calendar keywords and the special days to leave out.

For the tide, first add the *PEGELONLINE* integration, which comes with Home
Assistant, and pick the station "HAMBURG ST. PAULI". Moin Hamburg reads its
water level every quarter of an hour. Other gauges are refused: the tide marks
are those of St. Pauli. Without the gauge the Elbe stands as at high tide.

### Calendar keywords

A keyword matches the start of an event title up to the end of a word,
ignoring case; `*` stands for any text. Birthdays take the name from the rest
of the title.

| Day | default keywords | matches, for example |
|---|---|---|
| Birthday | `Geburtstag`, `Birthday`, `*'s birthday` | "Geburtstag Kim", "Sam's birthday" |
| Harbour birthday | `Hafengeburtstag`, `Harbour birthday`, `Port anniversary` | "Hafengeburtstag" |
| Cherry blossom festival | `Kirschblütenfest`, `Cherry blossom festival` | "Kirschblütenfest mit Feuerwerk" |
| Pride | `CSD`, `Pride` | "CSD Hamburg" |
| Blue Port | `Blue Port` | "Blue Port 2027" |
| Dom | `Dom`, `Hamburger Dom`, `Frühlingsdom`, `Sommerdom`, `Winterdom` | "Dom: Winterdom", but not "Domführung" |
| School holidays | `*ferien`, `School holidays` | "Herbstferien", but not "Ferienwohnung" |

## Themes and entities

Two themes, both dark: **moin-hamburg** (animated while the switch is on) and
**moin-hamburg-still** (never moves; for wall tablets and old phones). The
images are served from `/moin_hamburg/`; the newest 24 states stay on disk.
Like everything below `www/`, they need no login, so their names come from a
random secret of your installation rather than from the state key -- see
[SECURITY.md](SECURITY.md).

| Entity | |
|---|---|
| `sensor.moin_hamburg_skyline` | the state key, e.g. `night-cloudy.autumn.wind-calm.event-dom`; attributes for each part and the image URLs |
| `image.moin_hamburg_skyline` | the picture itself, for picture cards: animated while the switch is on; behind the login |
| `sensor.moin_hamburg_greeting` | "Good morning" ...; attribute `wish`, e.g. "Happy birthday, Kim!" |
| `sensor.moin_hamburg_summary` | "12° · Rain until about 15:00, then dry" |
| `sensor.moin_hamburg_special_day` | the special day drawn; attribute `all` lists every one of the moment |
| `switch.moin_hamburg_animated` | animation on or off |

Texts follow the Home Assistant language: German or English. The entity IDs
are the same in every language.

For a bug report, attach the diagnostics (*Settings → Devices & services →
Moin Hamburg → ⋮ → Download diagnostics*). They leave out calendar titles,
names and the image URLs.

A header for the dashboard:

```yaml
type: markdown
content: |
  ## {{ states('sensor.moin_hamburg_greeting') }}
  {{ state_attr('sensor.moin_hamburg_greeting', 'wish') }}
  {{ states('sensor.moin_hamburg_summary') }}
```

## Development

Two parts are plain Python with no dependencies and no Home Assistant imports:

* `custom_components/moin_hamburg/render/` -- the renderer: state key in, SVG out.
* `custom_components/moin_hamburg/state.py` -- the state: weather, sun,
  warnings and calendar titles in, state key and dashboard texts out.

These tests run without anything installed:

```sh
python3 tests/test_golden.py                 # 199 cases, byte for byte
python3 tests/test_state.py                  # state logic
python3 tests/test_showcase.py               # showcase examples, page, READMEs
python3 tools/gallery.py out/                # all cases as SVG + out/index.html
python3 tools/gallery.py out/ night-cloudy.autumn.wind-calm.event-dom
```

A state key names everything the picture shows, see
`custom_components/moin_hamburg/render/__init__.py`.

The showcase is built from the same code: `tools/showcase.py site out/` writes
the page with the renderer for Pyodide, a still picture per special day and
the README animation (that part needs Google Chrome and Pillow; `--no-gif`
leaves it out). Serve `out/` over HTTP to try it, e.g. `python3 -m http.server
-d out`. A workflow publishes it to GitHub Pages on every push to `main`.

The integration tests need the Home Assistant test harness; they also compare
the moon phase with Home Assistant's moon sensor for every day from 1990 to
2060:

```sh
uv venv .venv && uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest
```

This README exists in English and German; whoever changes one updates the other.

## License

MIT
