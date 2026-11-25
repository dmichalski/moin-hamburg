"""Constants for Moin Hamburg."""
import logging

DOMAIN = 'moin_hamburg'
LOGGER = logging.getLogger(__package__)

CONF_WEATHER = 'weather'
CONF_WARNINGS = 'warnings'
CONF_EVENT_CALENDARS = 'event_calendars'
CONF_BIN_CALENDARS = 'bin_calendars'
CONF_WATER_LEVEL = 'water_level'
# The gauge whose tide marks state.py knows: PEGELONLINE's sensor for Hamburg St. Pauli has this unique ID.
ST_PAULI_WATER_LEVEL = 'd488c5cc-4de9-4631-8ce1-0db0e700b546_water_level'
CONF_DEFAULT_THEME = 'default_theme'
CONF_KEYWORDS = 'keywords'
CONF_DISABLED_DAYS = 'disabled_days'

THEME = 'moin-hamburg'
THEME_STILL = 'moin-hamburg-still'
URL_PATH = '/moin_hamburg'
IMAGE_DIR = ('www', 'moin_hamburg')       # below the configuration folder
THEME_FILE = ('themes', 'moin-hamburg.yaml')
KEEP_IMAGES = 24                          # keys whose images stay on disk
STORAGE_KEY = f'{DOMAIN}.memory'
STORAGE_VERSION = 1

ISSUE_THEMES_NOT_LOADED = 'themes_not_loaded'
