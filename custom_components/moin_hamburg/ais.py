"""The optional AIS feed: one websocket to aisstream.io for the harbour window, open while Moin Hamburg runs.

Only with an API key in the options. Sent: the key and the window (ships.WINDOW). Received: the AIS reports of the
ships in it. A dropped connection is opened again after a pause that grows from ten seconds to ten minutes. The
picture is redrawn only when the set of big ships to show changes; the quarter-hour updates notice ships that left.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
from collections.abc import Awaitable, Callable

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from . import ships
from .const import LOGGER

CHECK_TIMEOUT = 15               # seconds for the key check in the options
RETRY_FIRST, RETRY_MAX = 10, 600  # seconds


class Refused(Exception):
    """aisstream.io answered with an error or closed the connection."""


class AisFeed:
    def __init__(self, hass: HomeAssistant, key: str, on_change: Callable[[], Awaitable[None]]) -> None:
        self.hass, self.key, self.on_change = hass, key, on_change
        self.harbour = ships.Harbour()
        self.connected = False
        self.messages = 0
        self.last_message: dt.datetime | None = None
        self.last_error: str | None = None
        self._shown: frozenset = frozenset()

    def shown(self) -> frozenset:
        return self.harbour.shown(dt_util.utcnow())

    async def run(self) -> None:
        """Keep the connection; runs until Home Assistant cancels it with the config entry."""
        delay = RETRY_FIRST
        while True:
            heard = self.messages
            try:
                await self._listen()
            except (aiohttp.ClientError, TimeoutError, ValueError, Refused) as err:
                self.last_error = str(err).replace(self.key, '**REDACTED**') or type(err).__name__
                LOGGER.debug('AIS connection ended: %s', self.last_error)
            except Exception:  # a bug must not end the feed for good
                self.last_error = 'unexpected error, see the log'
                LOGGER.exception('AIS feed failed')
            self.connected = False
            delay = RETRY_FIRST if self.messages > heard else min(delay * 2, RETRY_MAX)
            await asyncio.sleep(delay)

    async def _listen(self) -> None:
        async with async_get_clientsession(self.hass).ws_connect(ships.URL, heartbeat=30, compress=15) as ws:
            await ws.send_json(ships.subscription(self.key))
            async for msg in ws:
                if msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                    await self._handle(json.loads(msg.data))
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    raise Refused(str(ws.exception()))
            raise Refused(f'closed by the server ({ws.close_code})')

    async def _handle(self, data) -> None:
        if isinstance(data, dict) and data.get('error'):
            raise Refused(str(data['error']))
        now = dt_util.utcnow()
        self.connected, self.last_error = True, None
        self.messages += 1
        self.last_message = now
        self.harbour.feed(data, now)
        shown = self.harbour.shown(now)
        if shown != self._shown:
            self._shown = shown
            await self.on_change()

    def diagnostics(self) -> dict:
        return {'connected': self.connected, 'messages': self.messages,
                'last_message': self.last_message.isoformat() if self.last_message else None,
                'last_error': self.last_error, **self.harbour.summary(dt_util.utcnow())}


async def async_check_key(hass: HomeAssistant, key: str) -> str | None:
    """None if aisstream.io takes the key, else the error for the options form."""
    try:
        async with asyncio.timeout(CHECK_TIMEOUT):
            async with async_get_clientsession(hass).ws_connect(ships.URL, compress=15) as ws:
                await ws.send_json(ships.subscription(key))
                msg = await ws.receive()
                if msg.type in (aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY):
                    data = json.loads(msg.data)
                    return 'ais_invalid_key' if isinstance(data, dict) and data.get('error') else None
                return 'ais_invalid_key'  # closed without a word: that is how a refused key looks
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return 'ais_cannot_connect'
