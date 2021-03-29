"""Helper module to interface with Personal Tempest weather station."""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with Tempest personal weather
# station data
#

import json
import urllib3
from wg_helper import wg_error_print
from wg_helper import wg_trace_print
from wg_helper import wg_trace_pprint
# Tempest device parameters
from tempest_account_settings import PWS_TOKEN
from tempest_account_settings import PWS_DeviceID

# observation fields
tempest_obs_TimeEpoch       = 0
tempest_obs_WindLull        = 1
tempest_obs_WindAvg         = 2
tempest_obs_WindGust        = 3
tempest_obs_WindDir         = 4
tempest_obs_WindSampInt     = 5
tempest_obs_StaPressure     = 6
tempest_obs_AirTemp         = 7
tempest_obs_RelHumid        = 8
tempest_obs_Illum           = 9
tempest_obs_UV              = 10
tempest_obs_SolarRad        = 11
tempest_obs_PrecipAcc       = 12
tempest_obs_PrecipType      = 13
tempest_PT_none = 0
tempest_PT_rain = 1
tempest_PT_hail = 2
tempest_obs_LningAvgDist    = 14
tempest_obs_LningCnt        = 15
tempest_obs_Battery         = 16
tempest_obs_ReportInterval  = 17
tempest_obs_DayRainAcc      = 18
tempest_obs_RainAccFinal    = 19
tempest_obs_DayRainAccFinal = 20
tempest_obs_PrecipAnalysis  = 21
tempest_PA_none     = 0
tempest_PA_disp_on  = 1
tempest_PA_disp_off = 2

TEMPEST_VERSION = "1.0"

Trace = False

###############################################################################
#
# Get weather data from Tempest personal weather station
#
def getPWSdata(dsd):
    wind_directions = ["N", "NNE", "NE", "ENE",
                       "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW",
                       "W", "WNW", "NW", "NNW"]

    try:
        status = 0
        pman = urllib3.PoolManager()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ret = pman.request('GET', 'https://swd.weatherflow.com/swd/rest/' +
                           'observations/?device_id=' + PWS_DeviceID +
                           '&token=' + PWS_TOKEN)
        #wg_trace_pprint(ret.data, True)
        status = 1
        curr = json.loads(ret.data.decode('utf-8'))
        #wg_trace_pprint(curr, True)
        temp_c = curr['obs'][0][tempest_obs_AirTemp]
        dsd['temp_f'] = int(round(((temp_c * 9 / 5) + 32), 0))
        dsd['relative_humidity'] = str(int(curr['obs'][0][tempest_obs_RelHumid]))
        dsd['wind_dir'] = (wind_directions[int(((curr['obs'][0][tempest_obs_WindDir] /
                           22.5)+.5) % 16)])
        dsd['wind_mph'] = (curr['obs'][0][tempest_obs_WindAvg] * 2.237)
        dsd['wind_gust_mph'] = (curr['obs'][0][tempest_obs_WindGust] * 2.237)
        if type(curr['obs'][0][tempest_obs_StaPressure]) == type(None) :
            wg_trace_print("Barometric Pressure failed", True)
            dsd['pressure_in'] = "0" # something wrong with call ... next time
        else :
            dsd['pressure_in'] = str(round(curr['obs'][0][tempest_obs_StaPressure] / 33.8639, 2))
        temp_c = curr['summary']['feels_like']
        dsd['windchill'] = int(round(((temp_c * 9 / 5) + 32), 0))
        dsd['precip_today_in'] = round((curr['obs'][0][tempest_obs_DayRainAcc] / 25.4), 2)
        return True
    except ValueError:
        wg_error_print("getPWSdata", "Weather Collection Error #1 (status = " +
                       str(status) + ")")
    return False
