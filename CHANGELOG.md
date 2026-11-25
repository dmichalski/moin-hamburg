# Changelog

What changed for you in each release. The Marketplace shows the same text when it offers an update.

From 1.0 on, the version numbers follow [Semantic Versioning](https://semver.org/): the options, the entity IDs
and the parts of the state key stay as they are until 2.0.

## 1.0.0 – unreleased

**Home matches.** Two new special days, by keyword in your calendars, while the match lasts: the floodlights of
the Millerntor for FC St. Pauli, just behind the Elbphilharmonie, and those of the Volksparkstadion for the HSV,
far off in the west. Fixture lists name the home side first, so the default keywords (`FC St. Pauli`,
`Hamburger SV`, `HSV`, ...) find the home matches only. A match beats the Dom and the school holidays.

**Hamburger Schnack.** A new option for German: "Moin" all day, "Schietwetter" for rain, "Waschküche" for fog,
"Kaiserwetter" for a clear day, and the wishes in Low German.

**Ships.** Optional, with a free key from aisstream.io: a cruise ship lying at a terminal and big container
ships under way, from live AIS reports. Moin Hamburg then keeps one connection to aisstream.io and sends only the
key and a window around the harbour. Without a key nothing changes, and no connection is made. The diagnostics
show the state of the feed, never the key.

**Showcase page:** home matches and ships to try out; the page no longer mixes renderer files of two versions
from the browser cache.

## 0.3.0 – 2026-11-25

**Tide and storm surge.** A new optional field for the water level at the gauge Hamburg St. Pauli (Home
Assistant's own PEGELONLINE integration). The Elbe rises and falls in five steps from mean low to mean high tide
and bares a wet quay wall at low water. From 1.5 m above mean high tide the gauge brings the storm surge on its
own. Other gauges are refused: the tide marks are those of St. Pauli.

**Ice drift.** After four days of frost without a break, pack ice drifts down the Elbe and ice rims the quay; it
goes two days after the frost ends.

**Image entity.** `image.moin_hamburg_skyline`: the picture of the moment for picture cards, animated while the
switch is on, behind the login.

**Diagnostics** for bug reports, without calendar titles, names or image URLs.

Version 0.2.0 was never released; its changes are part of 0.3.0.

## 0.1.1 – 2026-11-22

An icon of its own: the skyline at dusk. Home Assistant shows it instead of "icon not available".

## 0.1.0 – 2026-11-22

First release: the drawn Hamburg skyline as dashboard background, following the weather, wind, season, moon,
warnings and Hamburg's special days; greeting and summary for the dashboard header; themes `moin-hamburg` and
`moin-hamburg-still`.
