#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a ThingSpeak account

WGThingSpeak_version = "1.01"

from urllib3 import PoolManager
import json
from urllib.request import urlretrieve, urlopen
import pprint

from WGHelper import *

# You'll need to create your own TSChannelsAndKeys.py file
from TSChannelsAndKeys import *

ThingSpeak_float_ERROR = -999.0

###############################################################################
#
# Get data from the ThingSpeak channel
def ThingSpeakGetFloat(chan, field, trace) :
    try :
        if chan == TS_BASEMENT_CHAN :
            key = TS_BASEMENT_API_READKEY
            nresults = "2"
            chanstr = "basement"
        else :
            WGErrorPrint("ThingSpeakGetFloat", "Invalid channel arg: " + str(chan))
            return ThingSpeak_float_ERROR
        pm = PoolManager()
        # Get the requested field from the specified ThingSpeak channel
        r = pm.request('GET', 'http://api.thingspeak.com/channels/'
                        + chan
                        + '/fields/'
                        + field
                        + '.json?api_key='
                        + key
                        + '&results='
                        + nresults)
        bt = json.loads(r.data.decode('utf-8'))
        retval = bt['feeds'][0]['field'+field]
        if trace :
            WGTracePrint("field " + field + " of " + chanstr + " channel = " + retval)
        return float(retval)
    except :
        WGErrorPrint("ThingSpeakGetFloat", "Exception getting field " + field + " from " + chanstr + " channel")
        return ThingSpeak_float_ERROR

###############################################################################
#
# Send 2 pieced of data to a ThingSpeak channel
#
def ThingSpeakSendFloatNum(chan, numfields, field1, value1, field2, value2, field3, value3, field4, value4, trace) :
    try :
        if numfields < 1 or numfields > 4 :
            WGErrorPrint("ThingSpeakSendFloatNum", "Invalid numfields arg (1, 2, or 3 expected): " + str(numfields))
            return
        if chan == TS_THERM_CHAN :
            key = TS_THERM_API_KEY
            chanstr = "thermostat"
        elif chan == TS_WEATHER_CHAN :
            key = TS_WEATHER_API_KEY
            chanstr = "WeatherUnderground"
        else :
            WGErrorPrint("ThingSpeakSendFloatNum", "Invalid channel arg: " + str(chan))
        pm = PoolManager()
        req = 'http://api.thingspeak.com/update?api_key=' + key + '&field' + field1 + '=' + str(value1)
        if numfields > 1 :
            req = req + '&field' + field2 + '=' + str(value2)
        if numfields > 2 :
            req = req + '&field' + field3 + '=' + str(value3)        
        if numfields > 3 :
            req = req + '&field' + field4 + '=' + str(value4)        
        # Get the requested field from the specified ThingSpeak channel
        r = pm.request('GET', req)
        if trace :
            WGTracePrint("STATUS = " + str(r.status))
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(r.data)
            pp.pprint(r.headers)
    except :
        WGErrorPrint("ThingSpeakSendFloat", "Exception sending data to field " + field + " from " + chanstr + " channel")

