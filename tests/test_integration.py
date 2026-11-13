"""The integration in Home Assistant: setup, entities, files on disk, theme, options, removal."""
import datetime as dt
import pathlib
import re

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from conftest import hourly
from custom_components.moin_hamburg import files
from custom_components.moin_hamburg.const import DOMAIN

TZ = 'Europe/Berlin'
OPTIONS = {'weather': 'weather.home', 'warnings': [], 'event_calendars': ['calendar.events'],
           'bin_calendars': ['calendar.bins'], 'default_theme': False}
SKYLINE, SPECIAL_DAY = 'sensor.moin_hamburg_skyline', 'sensor.moin_hamburg_special_day'
GREETING, SUMMARY = 'sensor.moin_hamburg_greeting', 'sensor.moin_hamburg_summary'
ANIMATED = 'switch.moin_hamburg_animated'


def local(text):
    return dt.datetime.fromisoformat(text).replace(tzinfo=dt_util.get_time_zone(TZ))


async def start(hass, fakes, freezer, when, *, condition='sunny', attributes=None, options=None, setup=True):
    await hass.config.async_set_time_zone(TZ)
    now = local(when)
    freezer.move_to(now)
    hass.states.async_set('weather.home', condition, {
        'temperature': 10, 'temperature_unit': '°C', 'wind_speed_unit': 'km/h', 'wind_gust_speed': 20,
        'wind_bearing': 270, **(attributes or {})})
    if not fakes.forecast:
        fakes.forecast = hourly(now, [condition] * 12)
    fakes.calendars.setdefault('calendar.events', [])
    fakes.calendars.setdefault('calendar.bins', [])
    entry = MockConfigEntry(domain=DOMAIN, title='Moin Hamburg', data={}, options={**OPTIONS, **(options or {})})
    entry.add_to_hass(hass)
    if setup:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def config(hass, *parts):
    return pathlib.Path(hass.config.path(*parts))


async def test_setup_draws_and_writes_the_theme(hass, fakes, freezer):
    fakes.calendars['calendar.events'] = [(local('2026-12-24 00:00'), local('2026-12-25 00:00'), 'Geburtstag Kim')]
    entry = await start(hass, fakes, freezer, '2026-12-24 12:00')
    assert entry.state is ConfigEntryState.LOADED

    sky = hass.states.get(SKYLINE)
    key = sky.state
    assert key == 'day-clear.winter.wind-calm.event-birthday'
    assert sky.attributes['scene'] == 'day-clear' and sky.attributes['special_day'] == 'birthday'
    image, still = sky.attributes['image'], sky.attributes['still_image']
    assert re.fullmatch(r'/moin_hamburg/[0-9a-f]{32}\.svg\?v=[0-9a-f]{12}', image), image
    assert still.startswith(image.split('.svg')[0] + '-still.svg?v='), still
    day = hass.states.get(SPECIAL_DAY)
    assert day.state == 'birthday'
    assert day.attributes['all'] == ['birthday', 'christmas'] and day.attributes['name'] == 'Kim'
    greeting = hass.states.get(GREETING)
    assert (greeting.state, greeting.attributes['wish']) == ('Good afternoon', 'Happy birthday, Kim!')
    assert hass.states.get(SUMMARY).state == '10° · Fair, up to 10°'
    assert hass.states.get(ANIMATED).state == 'on'

    folder = config(hass, 'www', 'moin_hamburg')
    assert (folder / image.split('/')[-1].split('?')[0]).read_text().startswith('<svg')
    assert (folder / still.split('/')[-1].split('?')[0]).exists()
    assert not any('birthday' in p.name for p in folder.iterdir())
    theme = config(hass, 'themes', 'moin-hamburg.yaml').read_text()
    assert theme.startswith('# Moin Hamburg') and 'moin-hamburg:\n' in theme and 'moin-hamburg-still:\n' in theme
    assert sky.attributes['image'] in theme and sky.attributes['still_image'] in theme
    assert fakes.reloads == 1 and not fakes.default_theme
    assert ir.async_get(hass).async_get_issue(DOMAIN, 'themes_not_loaded') is None


async def test_units_bearing_and_dwd_warnings(hass, fakes, freezer):
    now = local('2026-11-10 12:00')
    fakes.forecast = hourly(now, ['cloudy'] * 12, temperature=50, gust=12)
    hass.states.async_set('sensor.dwd_level', '2', {'warning_count': 1, 'warning_1_name': 'STURMBÖEN',
                                                    'warning_1_headline': 'Amtliche WARNUNG vor STURMBÖEN'})
    await start(hass, fakes, freezer, '2026-11-10 12:00', condition='cloudy', options={'warnings': ['sensor.dwd_level']},
                attributes={'temperature': 50, 'temperature_unit': '°F', 'wind_speed_unit': 'm/s', 'wind_gust_speed': 12,
                            'wind_bearing': 'E'})
    assert hass.states.get(SKYLINE).state == 'day-cloudy.autumn.wind-windy-east.warning-storm-gusts'
    assert hass.states.get(SKYLINE).attributes['gust'] == 43
    assert hass.states.get(SUMMARY).state == '10° · Cloudy, up to 10°'


async def test_nina_headline_attribute_or_sensor(hass, fakes, freezer):
    registry = er.async_get(hass)
    old = registry.async_get_or_create('binary_sensor', 'nina', '020000000000-1', suggested_object_id='warning_1').entity_id
    new = registry.async_get_or_create('binary_sensor', 'nina', '020000000000-2', suggested_object_id='warning_2').entity_id
    headline = registry.async_get_or_create('sensor', 'nina', '020000000000-2-headline',
                                            suggested_object_id='warning_2_headline').entity_id
    hass.states.async_set(old, 'off')
    hass.states.async_set(new, 'on', {'id': 'x'})  # Home Assistant 2026.11: no headline attribute any more
    hass.states.async_set(headline, 'Amtliche UNWETTERWARNUNG vor ORKANBÖEN')
    await start(hass, fakes, freezer, '2026-11-10 12:00', options={'warnings': [old, new]})
    assert hass.states.get(SKYLINE).attributes['warning'] == 'hurricane'

    # a warning before 2026.11, with the headline on the binary sensor: the newer state wins
    hass.states.async_set(old, 'on', {'headline': 'Amtliche WARNUNG vor STURMFLUT'})
    hass.states.async_set(new, 'off')
    await hass.async_block_till_done()
    freezer.tick(dt.timedelta(seconds=15))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    sky = hass.states.get(SKYLINE)
    assert sky.attributes['warning'] == 'storm-surge' and 'storm-surge' in sky.attributes['extremes']


async def test_animated_switch(hass, fakes, freezer):
    await start(hass, fakes, freezer, '2026-11-10 12:00')
    sky = hass.states.get(SKYLINE)
    animated, still = sky.attributes['image'], sky.attributes['still_image']
    theme_file = config(hass, 'themes', 'moin-hamburg.yaml')

    def theme_image(name):
        block = theme_file.read_text().split(f'\n{name}:\n')[1]
        return block.split('url("')[1].split('")')[0]

    assert (theme_image('moin-hamburg'), theme_image('moin-hamburg-still')) == (animated, still)
    await hass.services.async_call('switch', 'turn_off', {'entity_id': ANIMATED}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(ANIMATED).state == 'off'
    assert (theme_image('moin-hamburg'), theme_image('moin-hamburg-still')) == (still, still)
    await hass.services.async_call('switch', 'turn_on', {'entity_id': ANIMATED}, blocking=True)
    await hass.async_block_till_done()
    assert theme_image('moin-hamburg') == animated and fakes.reloads == 3


async def test_quarter_hours_and_new_years_eve(hass, fakes, freezer):
    await start(hass, fakes, freezer, '2026-12-31 17:50')
    assert hass.states.get(SPECIAL_DAY).state == 'none'
    freezer.move_to(local('2026-12-31 18:00:10'))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    freezer.tick(dt.timedelta(seconds=15))  # past the debounce
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SPECIAL_DAY).state == 'new-years-eve'
    assert hass.states.get(GREETING).attributes['wish'] == 'Happy New Year’s Eve!'
    assert fakes.reloads == 2


async def test_bin_day_and_a_broken_calendar(hass, fakes, freezer):
    fakes.calendars['calendar.bins'] = [(local('2026-10-16 08:00'), local('2026-10-16 09:00'), 'Restmüll')]
    await start(hass, fakes, freezer, '2026-10-16 07:00',
                options={'event_calendars': ['calendar.gone', 'calendar.events']})
    assert hass.states.get(SPECIAL_DAY).state == 'bin-day'


async def test_german(hass, fakes, freezer):
    hass.config.language = 'de'
    await start(hass, fakes, freezer, '2026-11-10 08:00')
    assert hass.states.get(GREETING).state == 'Guten Morgen'


async def test_themes_not_loaded(hass, fakes, freezer):
    fakes.themes_loaded = False
    await start(hass, fakes, freezer, '2026-11-10 12:00')
    assert ir.async_get(hass).async_get_issue(DOMAIN, 'themes_not_loaded') is not None


async def test_default_theme(hass, fakes, freezer):
    await start(hass, fakes, freezer, '2026-11-10 12:00', options={'default_theme': True})
    assert fakes.default_theme == [{'name': 'moin-hamburg', 'name_dark': 'moin-hamburg'}]


async def test_weather_unavailable(hass, fakes, freezer):
    entry = await start(hass, fakes, freezer, '2026-11-10 12:00', setup=False)
    hass.states.async_set('weather.home', 'unavailable')
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_remove(hass, fakes, freezer):
    entry = await start(hass, fakes, freezer, '2026-11-10 12:00')
    assert config(hass, 'themes', 'moin-hamburg.yaml').exists()
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not config(hass, 'themes', 'moin-hamburg.yaml').exists()
    assert not config(hass, 'www', 'moin_hamburg').exists()
    assert fakes.reloads == 2


def test_old_images_are_pruned(tmp_path, monkeypatch):
    monkeypatch.setattr(files, 'KEEP_IMAGES', 2)
    f = files.Files(tmp_path / 'img', tmp_path / 'themes' / 'moin-hamburg.yaml', secret='s1')
    f.prepare()
    (tmp_path / 'img' / 'day-clear.winter.wind-calm.svg').write_text('<svg/>')   # named by an older version
    for key in ('day-clear.spring.wind-calm', 'day-clear.summer.wind-calm', 'day-clear.autumn.wind-calm'):
        f.write(key, 'day-clear', True)
    keep = ('day-clear.autumn.wind-calm', 'day-clear.summer.wind-calm')
    assert sorted(p.name for p in (tmp_path / 'img').iterdir()) == sorted(
        f.image_name(k, s) for k in keep for s in ('', '-still'))


def test_image_names_hide_the_key():
    a = files.Files('img', 'theme.yaml', secret='s1')
    b = files.Files('img', 'theme.yaml', secret='s2')
    key = 'day-clear.winter.wind-calm.event-birthday'
    assert a.image_name(key) != b.image_name(key) and 'birthday' not in a.image_name(key)
    assert a.image_name(key) == files.Files('img', 'theme.yaml', secret='s1').image_name(key)
    with pytest.raises(ValueError):
        files.Files('img', 'theme.yaml').image_name(key)


async def test_image_names_survive_a_restart(hass, fakes, freezer):
    entry = await start(hass, fakes, freezer, '2026-12-10 12:00')
    image = hass.states.get(SKYLINE).attributes['image']
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(SKYLINE).attributes['image'] == image


async def test_config_and_options_flow(hass, fakes, freezer):
    await hass.config.async_set_time_zone(TZ)
    freezer.move_to(local('2026-12-10 12:00'))
    hass.states.async_set('weather.home', 'sunny', {'temperature': 4})
    fakes.forecast = hourly(local('2026-12-10 12:00'), ['sunny'] * 12)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={'source': 'user'})
    assert result['type'] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result['flow_id'], {'weather': 'weather.home'})
    assert result['type'] is FlowResultType.CREATE_ENTRY
    entry = result['result']
    assert entry.options == {'weather': 'weather.home', 'warnings': [], 'event_calendars': [], 'bin_calendars': [],
                             'default_theme': False}
    await hass.async_block_till_done()
    assert hass.states.get(SPECIAL_DAY).state == 'advent'

    again = await hass.config_entries.flow.async_init(DOMAIN, context={'source': 'user'})
    assert again['type'] is FlowResultType.ABORT and again['reason'] == 'single_instance_allowed'

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result['type'] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result['flow_id'], {
        'weather': 'weather.home', 'keywords': {'dom': ' Jahrmarkt,, Kirmes '}, 'disabled_days': ['advent']})
    assert result['type'] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options['keywords']['dom'] == 'Jahrmarkt, Kirmes'
    assert entry.options['keywords']['birthday'] == ''
    assert entry.options['disabled_days'] == ['advent']
    assert hass.states.get(SPECIAL_DAY).state == 'none'  # reloaded with the new options
