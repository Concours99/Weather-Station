# Weather-Station
Python code for Raspberry Pi weather station project

Several python packages must be installed for this code to work:
ephem
logzero
openpyxl
twilio

There are several files you will need to supply.  I separated these definitions out as they are specific to my personal
accounts on the various websites.

thingspeak_channels_keys.py

This file contains the ThinkSpeak.com channel and field definitions as well as the keys needed to read and write values.
These are the definitions needed to work with the current code ...

TS_THERM_CHAN
TS_THERM_API_KEY
TS_THERM_API_READKEY
TS_BASEMENT_CHAN
TS_BASEMENT_API_KEY
TS_BASEMENT_API_READKEY
TS_WEATHER_CHAN
TS_WEATHER_API_KEY
TS_WEATHER_API_READKEY

twilio_account_settings.py

This file contains the definitions for your Twilio.com account.
These are the definitions needed to work with the current code ...

TWILIO_ACT
TWILIO_AUTH_TOKEN
CELL_PHONE
FROM_PHONE

dark_sky_account_settings.py

This file contains the definitions for your DarkSky.net account.
These are the definitions needed to work with the current code ...

DS_API_KEY
DS_LAT
DS_LON