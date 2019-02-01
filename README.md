# Weather-Station
Python code for Raspberry Pi weather station project

There are several files you will need to supply.  I seperated these definitions out as they are specific to my personal
accounts on the various websites.

TSChannelsAndKeys.py

This file contains the ThinSpeak.com channel and field definitions as well as the keys needed to read and write values.
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

TWAccountSettings.py

This file contains the definitions for your Twilio.com account.
These are the definitions needed to work with the current code ...

TWILIO_ACT
TWILIO_AUTH_TOKEN
CELL_PHONE
FROM_PHONE

WUAccountSettings.py

This file contains the definitions for your WeatherUnderground.com account.
These are the definitions needed to work with the current code ...

WU_API_KEY
WU_STATE_CODE
WU_PWS # a list of personal weather stations you want to cycle through to get the weather