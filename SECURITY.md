# Security

## Reporting a vulnerability

Please report it privately: *Security → Report a vulnerability* on this
repository. Please don't open a public issue for it. You will get an answer
within a week.

Only the latest release gets fixes.

## What the integration does

* It has no dependencies beyond Home Assistant. It reads the weather, the sun,
  the warning sensors, calendars and the water level sensor you choose, and
  nothing else.
* Without an aisstream.io key it makes no network connections. With one, it
  keeps a single websocket to `stream.aisstream.io` and sends the key and a
  fixed window around the Hamburg harbour, nothing about your home. Home
  Assistant stores the key with the integration's options, like any other
  integration's credentials; the diagnostics leave it out.
* It writes into the configuration folder:
  * images to `www/moin_hamburg/`
  * the themes to `themes/moin-hamburg.yaml`
  * its memory to `.storage/moin_hamburg.memory`

  Removing the integration deletes all three.
* Home Assistant serves the images at `/moin_hamburg/` without a login, like
  everything below `www/`. The file names come from a random secret of each
  installation, not from the state key, so nobody can probe which picture is
  showing (a birthday, the school holidays).
* Names from birthday events appear in the greeting, never in the picture.
* `image.moin_hamburg_skyline` serves the same picture through Home
  Assistant's image proxy, which needs a login.
