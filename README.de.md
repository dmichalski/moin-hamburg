# Moin Hamburg

[English](README.md) · **Deutsch**

Eine lebendige Hamburger Skyline für Home Assistant: ein gezeichnetes
Hafenpanorama als Dashboard-Hintergrund, das Wetter, Wind, Jahreszeit, Mond,
Sturmwarnungen und Hamburgs besonderen Tagen folgt -- das Riesenrad vom Dom im
Herbst, Großsegler zum Hafengeburtstag, Laternen an St. Martin, Feuerwerk zu
Silvester.

![Die Skyline durchs Jahr: Sommer, Hafengeburtstag, Regen, eine Sturmwarnung,
der Dom, St. Martin, Schnee, Weihnachten, Silvester, Feuerwerk zum
Kirschblütenfest, CSD und ein heißer Abend](https://dmichalski.github.io/moin-hamburg/showcase.gif)

**[Jedes Bild im Browser ausprobieren](https://dmichalski.github.io/moin-hamburg/)**
-- mit dem echten Generator, direkt auf der Seite (englisch).

## Was das Bild zeigt

| | woher |
|---|---|
| Tag, Dämmerung, Nacht | Sonnenhöhe (über 6°, bis -6°, darunter) |
| Klar, wolkig, Regen, Schnee | jetzt und die nächsten drei Vorhersagestunden |
| Ruhig, windig, Sturm; Wind aus Ost oder West | Böen jetzt und in den nächsten drei Stunden (40 und 75 km/h) |
| Frühling, Sommer, Herbst, Winter | der Monat |
| Mondphase | berechnet, so wie sie der Mond-Sensor von Home Assistant hat |
| Die Tide: Die Elbe fällt und legt die Kaimauer frei | der Pegel Hamburg St. Pauli, in fünf Stufen vom mittleren Niedrig- bis zum mittleren Hochwasser |
| Hitze, Kälte, Nebel, Gewitter, Schneedecke, Sturmflut | Temperaturen, Vorhersage, Warnungen; Schneedecke nach zwei Stunden Schnee bei 1 °C oder weniger, weg nach sechs Stunden über 3 °C; Sturmflut auch vom Pegel, ab 1,5 m über dem mittleren Hochwasser |
| Eisgang: Packeis auf der Elbe, Eis an der Kaimauer | vier Tage Frost ohne einen Wert über 0 °C; weg nach zwei Tagen ohne Frost |
| Sturmbälle am Signalmast | Sturm- und Orkanwarnungen |
| Große Schiffe: ein Kreuzfahrtschiff am Terminal, ein Containerschiff in Fahrt | AIS-Meldungen von aisstream.io, nur mit Schlüssel (siehe *Schiffe*) |
| Besondere Tage | das Datum, deine Kalender, die Müllabfuhr |

Gezeichnet wird immer nur ein besonderer Tag, der wichtigste: Ein stiller Tag
(Karfreitag, die Gedenktage im November) schlägt alles und hält das Bild ruhig,
dann kommt ein Geburtstag, dann einzelne Tage, dann Zeiträume (Dom, Ferien,
Advent), dann das Müllauto.

| Besonderer Tag | wann |
|---|---|
| Silvester, Neujahr | 31. Dezember ab 18 Uhr bis 1. Januar 2 Uhr; danach bis mittags |
| Heilige Drei Könige, Valentinstag, Fasching, Ostern, Christi Himmelfahrt, Muttertag, Halloween, St. Martin, Nikolaus, Weihnachten, Zeitumstellung, stille Tage, Advent | aus dem Datum berechnet |
| Sommersonnenwende | 20. bis 22. Juni |
| Sternschnuppen | 10. bis 14. August und 12. bis 15. Dezember, nach Sonnenuntergang |
| Erster Schnee | der Tag, an dem es zum ersten Mal 15 Minuten schneit, Oktober bis April |
| Geburtstag, Hafengeburtstag, Kirschblütenfest, CSD, Blue Port, Dom, Ferien | deine Kalender, über Stichworte |
| Heimspiel FC St. Pauli (Flutlicht am Millerntor), Heimspiel HSV (am Volksparkstadion) | deine Kalender, über Stichworte, solange das Spiel läuft |
| Müllabfuhr | ein beliebiger Termin heute in einem Müllkalender, von 6 bis 10 Uhr morgens |

Namen aus Geburtstagen erscheinen nie im Bild, nur in der Begrüßung.

## Installation

[![Repository in deinem Home Assistant öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dmichalski&repository=moin-hamburg&category=integration)

* Home Assistant 2026.11 oder neuer: *Einstellungen → Marketplace*, oben rechts
  *Add from link*, `dmichalski/moin-hamburg` eingeben, dann herunterladen.
* Home Assistant 2026.9 und 2026.10: in HACS unter *Benutzerdefinierte
  Repositories* das Repository als *Integration* hinzufügen, dann herunterladen.
* Von Hand: `custom_components/moin_hamburg` in den Konfigurationsordner kopieren.

Danach Home Assistant neu starten.

Die Integration schreibt ihre Themes nach `themes/moin-hamburg.yaml`. Home
Assistant lädt Themes von dort, wenn in der `configuration.yaml` steht:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

Fehlt das, meldet die Integration es als Reparaturhinweis.

Was sich in welcher Version geändert hat: [CHANGELOG.md](CHANGELOG.md).

## Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → Moin Hamburg.*

| Feld | |
|---|---|
| Wetter | Pflicht; eine Wetter-Entität mit stündlicher Vorhersage (Met.no, DWD, ...) |
| Wetterwarnungen | optional; die Warn-Binärsensoren von NINA oder ihre Schlagzeilen-Sensoren, oder die DWD-Warnstufen-Sensoren |
| Kalender mit Hamburger Terminen, Geburtstagen und Ferien | optional; Termine zählen über ihren Titel |
| Kalender der Müllabfuhr | optional; ein Termin an einem Tag heißt Abholung |
| Wasserstand Hamburg St. Pauli | optional; der Wasserstands-Sensor des Pegels „HAMBURG ST. PAULI“ |
| Moin Hamburg als Standard-Theme setzen | für alle Benutzer und Geräte; sonst das Theme im Profil wählen |

In den Optionen kommen die Kalender-Stichworte, die besonderen Tage, die
wegbleiben sollen, der Hamburger Schnack und der Schlüssel für die Schiffe dazu.

Für die Tide zuerst die Integration *PEGELONLINE* hinzufügen, die Home
Assistant mitbringt, und die Station „HAMBURG ST. PAULI“ wählen. Moin Hamburg
liest ihren Wasserstand jede Viertelstunde. Andere Pegel lehnt der Dialog ab:
Die Tidemarken sind die von St. Pauli. Ohne Pegel steht die Elbe wie bei
Hochwasser.

Für die Heimspiele einen Kalender mit den Spielen zu den Kalendern mit
Hamburger Terminen nehmen: einen eigenen oder einen abonnierten Spielplan. In
Spielplänen steht der Gastgeber vorn, also leuchtet „FC St. Pauli – Werder
Bremen“ das Millerntor an und „Werder Bremen – FC St. Pauli“ nicht.

Der *Hamburger Schnack* (nur auf Deutsch) grüßt den ganzen Tag mit „Moin“,
nennt Regen „Schietwetter“, Nebel „Waschküche“ und einen klaren Tag
„Kaiserwetter“ und wünscht auf Platt: „Kumm goot röver!“ zu Silvester,
„Allens Gode, Kim!“ zum Geburtstag.

### Schiffe

Mit einem kostenlosen Schlüssel von [aisstream.io](https://aisstream.io) (mit
GitHub anmelden, dann *Account*) zeigt das Bild ein Kreuzfahrtschiff am
Terminal und große Containerschiffe in Fahrt, nach den AIS-Meldungen in
Echtzeit. Den Schlüssel in den Optionen eintragen; Moin Hamburg prüft ihn
einmal. Danach hält es eine Verbindung zu aisstream.io und sendet nur den
Schlüssel und einen Ausschnitt um den Hafen, vom Kreuzfahrtterminal Altona bis
zur HafenCity. aisstream.io gibt keine Garantie: Ist der Dienst weg, bleiben
die Schiffe eben weg. Ohne Schlüssel baut Moin Hamburg keine eigenen
Verbindungen auf.

### Kalender-Stichworte

Ein Stichwort passt auf den Anfang eines Termintitels bis zum Wortende,
Groß- und Kleinschreibung egal; `*` steht für beliebigen Text. Geburtstage
nehmen den Namen aus dem Rest des Titels.

| Tag | Stichworte ab Werk | passt zum Beispiel auf |
|---|---|---|
| Geburtstag | `Geburtstag`, `Birthday`, `*'s birthday` | „Geburtstag Kim“, „Sam's birthday“ |
| Hafengeburtstag | `Hafengeburtstag`, `Harbour birthday`, `Port anniversary` | „Hafengeburtstag“ |
| Kirschblütenfest | `Kirschblütenfest`, `Cherry blossom festival` | „Kirschblütenfest mit Feuerwerk“ |
| CSD | `CSD`, `Pride` | „CSD Hamburg“ |
| Blue Port | `Blue Port` | „Blue Port 2027“ |
| Dom | `Dom`, `Hamburger Dom`, `Frühlingsdom`, `Sommerdom`, `Winterdom` | „Dom: Winterdom“, aber nicht „Domführung“ |
| Ferien | `*ferien`, `School holidays` | „Herbstferien“, aber nicht „Ferienwohnung“ |
| Heimspiel FC St. Pauli | `FC St. Pauli`, `Heimspiel St. Pauli`, `Millerntor` | „FC St. Pauli – Werder Bremen“ |
| Heimspiel HSV | `Hamburger SV`, `HSV`, `Heimspiel HSV`, `Volksparkstadion` | „HSV – Hertha BSC“, aber nicht „Hertha BSC – HSV“ |

## Themes und Entitäten

Zwei Themes, beide dunkel: **moin-hamburg** (bewegt, solange der Schalter an
ist) und **moin-hamburg-still** (bewegt sich nie; für Wand-Tablets und alte
Telefone). Die Bilder liegen unter `/moin_hamburg/`; die neuesten 24 Zustände
bleiben auf der Platte. Wie alles unter `www/` sind sie ohne Anmeldung
erreichbar, deshalb kommen ihre Namen aus einem zufälligen Geheimnis deiner
Installation statt aus dem Zustandsschlüssel -- siehe
[SECURITY.md](SECURITY.md) (englisch).

| Entität | |
|---|---|
| `sensor.moin_hamburg_skyline` | der Zustandsschlüssel, z. B. `night-cloudy.autumn.wind-calm.event-dom`; Attribute für jeden Teil und die Bild-URLs |
| `image.moin_hamburg_skyline` | das Bild selbst, für Bildkarten: animiert, solange der Schalter an ist; nur angemeldet |
| `sensor.moin_hamburg_greeting` | „Guten Morgen“ ...; Attribut `wish`, z. B. „Alles Gute, Kim!“ |
| `sensor.moin_hamburg_summary` | „12° · Regen bis etwa 15 Uhr, danach trocken“ |
| `sensor.moin_hamburg_special_day` | der gezeichnete besondere Tag; das Attribut `all` listet alle des Moments |
| `switch.moin_hamburg_animated` | Animation an oder aus |

Die Texte folgen der Sprache von Home Assistant: deutsch oder englisch. Die
Entitäts-IDs sind in jeder Sprache gleich.

Für eine Fehlermeldung die Diagnose anhängen (*Einstellungen → Geräte &
Dienste → Moin Hamburg → ⋮ → Diagnose herunterladen*). Kalendertitel, Namen
und die Bild-URLs fehlen darin.

Eine Kopfzeile fürs Dashboard:

```yaml
type: markdown
content: |
  ## {{ states('sensor.moin_hamburg_greeting') }}
  {{ state_attr('sensor.moin_hamburg_greeting', 'wish') }}
  {{ states('sensor.moin_hamburg_summary') }}
```

## Entwicklung

Drei Teile sind reines Python, ohne Abhängigkeiten und ohne Imports aus Home
Assistant:

* `custom_components/moin_hamburg/render/` -- der Generator: Zustandsschlüssel
  rein, SVG raus.
* `custom_components/moin_hamburg/state.py` -- der Zustand: Wetter, Sonne,
  Warnungen und Kalendertitel rein, Zustandsschlüssel und Dashboard-Texte raus.
* `custom_components/moin_hamburg/ships.py` -- AIS-Meldungen rein, die großen
  Schiffe fürs Bild raus.

Diese Tests laufen ohne jede Installation:

```sh
python3 tests/test_golden.py                 # jeder Fall, Byte für Byte
python3 tests/test_state.py                  # Zustandslogik
python3 tests/test_ships.py                  # welche AIS-Meldungen zählen
python3 tests/test_showcase.py               # Showcase-Beispiele, Seite, READMEs
python3 tools/gallery.py out/                # alle Fälle als SVG + out/index.html
python3 tools/gallery.py out/ night-cloudy.autumn.wind-calm.event-dom
```

Ein Zustandsschlüssel benennt alles, was das Bild zeigt, siehe
`custom_components/moin_hamburg/render/__init__.py`.

Der Showcase entsteht aus demselben Code: `tools/showcase.py site out/` schreibt
die Seite mit dem Generator für Pyodide, ein Standbild je besonderem Tag und
die Animation für die README (dafür braucht es Google Chrome und Pillow;
`--no-gif` lässt sie weg). Zum Ausprobieren `out/` über HTTP ausliefern, etwa
mit `python3 -m http.server -d out`. Ein Workflow veröffentlicht sie bei jedem
Push auf `main` auf GitHub Pages.

Die Integrationstests brauchen die Testumgebung von Home Assistant; sie
vergleichen auch die Mondphase mit dem Mond-Sensor von Home Assistant für
jeden Tag von 1990 bis 2060:

```sh
uv venv .venv && uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest
```

Die README gibt es englisch und deutsch; wer eine ändert, zieht die andere nach.

## Lizenz

MIT
