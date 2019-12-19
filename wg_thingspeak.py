# pylint: disable=W0702
# pylint: disable=R0913
# pylint: disable=R0914

"""Interface with ThingSpeak account"""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a ThingSpeak account
import json
from urllib3 import PoolManager

from wg_helper import wg_error_print
from wg_helper import wg_trace_print
from wg_helper import wg_trace_pprint

# You'll need to create your own TSChannelsAndKeys.py file
from thingspeak_channels_keys import TS_BASEMENT_CHAN
from thingspeak_channels_keys import TS_THERM_CHAN
from thingspeak_channels_keys import TS_WEATHER_CHAN
from thingspeak_channels_keys import TS_WEATHER_API_KEY
from thingspeak_channels_keys import TS_THERM_API_KEY
from thingspeak_channels_keys import TS_BASEMENT_API_READKEY

WGTHINGSPEAK_VERSION = "2.0"

THINGSPEAK_FLOAT_ERROR = -999.0

###############################################################################
#
# Get data from the ThingSpeak channel
def thingspeakgetfloat(chan, field, trace):
    """Retrieve a floating point value from a ThingSpeak field"""
    try:
        if chan == TS_BASEMENT_CHAN:
            key = TS_BASEMENT_API_READKEY
            nresults = "2"
            chanstr = "basement"
        else:
            wg_error_print("thingspeakgetfloat", "Invalid channel arg: " + str(chan))
            return THINGSPEAK_FLOAT_ERROR
        pman = PoolManager()
        # Get the requested field from the specified ThingSpeak channel
        retstruct = pman.request('GET', 'http://api.thingspeak.com/channels/' +
                                 chan +
                                 '/fields/' +
                                 field +
                                 '.json?api_key=' +
                                 key +
                                 '&results=' +
                                 nresults)
        decodestruct = json.loads(retstruct.data.decode('utf-8'))
        retval = decodestruct['feeds'][0]['field'+field]
        wg_trace_print("field " + field + " of " + chanstr + " channel = " +
                       retval, trace)
    except:
        wg_error_print("thingspeakgetfloat", "Exception getting field " +
                       field + " from " + chanstr + " channel")
        return THINGSPEAK_FLOAT_ERROR
    return float(retval)

###############################################################################
#
# Send 2 pieced of data to a ThingSpeak channel
#
def thingspeaksendfloatnum(chan, numfields, field1, value1, field2, value2,
                           field3, value3, field4, value4, trace):
    """Update a floating point value on a channel field"""
    try:
        if numfields < 1 or numfields > 4:
            wg_error_print("thingspeaksendfloatnum",
                           "Invalid numfields arg (1, 2, or 3 expected): " +
                           str(numfields))
            return
        if chan == TS_THERM_CHAN:
            key = TS_THERM_API_KEY
            chanstr = "thermostat"
        elif chan == TS_WEATHER_CHAN:
            key = TS_WEATHER_API_KEY
            chanstr = "WeatherUnderground"
        else:
            wg_error_print("thingspeaksendfloatnum", "Invalid channel arg: " + str(chan))
        pman = PoolManager()
        req = ('http://api.thingspeak.com/update?api_key=' + key + '&field' +
               field1 + '=' + str(value1))
        if numfields > 1:
            req = req + '&field' + field2 + '=' + str(value2)
        if numfields > 2:
            req = req + '&field' + field3 + '=' + str(value3)
        if numfields > 3:
            req = req + '&field' + field4 + '=' + str(value4)
        # Get the requested field from the specified ThingSpeak channel
        retstruct = pman.request('GET', req)
        wg_trace_print("STATUS = " + str(retstruct.status), trace)
        wg_trace_pprint(retstruct.data, trace)
        wg_trace_pprint(retstruct.headers, trace)
    except:
        wg_error_print("ThingSpeakSendFloat",
                       "Exception sending data to " + chanstr + " channel")
