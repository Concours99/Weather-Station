#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a Radio Thermostat
#
# http://api.wunderground.com/api/a431ca16c744d357/alerts/astronomy/conditions/forecast/q/MA/pws:KMATEWKS6.json

WGWeatherUnderground_version = "1.02"

from urllib3 import PoolManager
import json
import pprint
import datetime
from WGHelper import *

# WeatherUnderground - requires an account
from WUAccountSettings import *

WU_Last_Observation_Epoch = 0
WU_Num_Calls_Made_Today = 0
WU_Today = 0

def MoonPhaseURL() :
    return "https://www.wunderground.com/graphics/moonpictsnew/"
    
###############################################################################
#
# Get weather data from WeatherUnderground
#
def GetWeatherData(WU) :
    global WU_Last_Observation_Epoch
    global WU_Num_Calls_Made_Today
    global WU_Today
    i = 1
    for PWS in WU_PWS :
        try:
            status = 0
            pm = PoolManager()
            r = pm.request('GET', 'http://api.wunderground.com/api/' + WU_API_KEY +
                            '/alerts/astronomy/conditions/forecast/q/' + WU_STATE_CODE +
                            '/pws:' + PWS + '.json')
            # if it's tomorrow, zero out the number of calls made today
            if WU_Today != datetime.date.today() :
                WU_Today = datetime.date.today()
                WU_Num_Calls_Made_Today = 0
            # add 1 to the number of calls made today
            WU_Num_Calls_Made_Today = WU_Num_Calls_Made_Today + 1
            status = 1
            co = json.loads(r.data.decode('utf-8'))['current_observation']
            if co['temp_f'] is None :
                WGErrorPrint("GetWeatherData", PWS +
                                " temp_f is None.  Calls Today = " +
                                str(WU_Num_Calls_Made_Today))
                continue
            if WU_Last_Observation_Epoch < int(co['observation_epoch']) :
                # we got new data
                WU_Last_Observation_Epoch = int(co['observation_epoch'])
                WU['pws'] = i
                WU['observation_time'] = str(datetime.datetime.fromtimestamp(WU_Last_Observation_Epoch).strftime('Upd: %Y-%m-%d %H:%M:%S (')) + PWS + ')'
                WU['weather'] = co['weather']
                WU['temp_f'] = co['temp_f']
                WU['temp_c'] = co['temp_c']
                WU['relative_humidity'] = co['relative_humidity']
                WU['wind_dir'] = co['wind_dir']
                WU['wind_mph'] = co['wind_mph']
                WU['wind_gust_mph'] = co['wind_gust_mph']
                WU['wind_kph'] = co['wind_kph']
                WU['wind_gust_kph'] = co['wind_gust_kph']
                WU['pressure_mb'] = co['pressure_mb']
                WU['pressure_in'] = co['pressure_in']
                WU['feelslike_f'] = co['feelslike_f']
                WU['feelslike_c'] = co['feelslike_c']
                WU['visibility_mi'] = co['visibility_mi']
                WU['visibility_km'] = co['visibility_km']
                WU['precip_today_in'] = co['precip_today_in']
                WU['precip_today_metric'] = co['precip_today_metric']
                status = 2
                fc = json.loads(r.data.decode('utf-8'))['forecast']
                i = 0
                WU['fc'] = [dict(), dict(), dict(), dict()]
                for day in fc['simpleforecast']['forecastday'] :
                    WU['fc'][i] = dict()
                    WU['fc'][i]['name'] = day['date']['weekday']
                    WU['fc'][i]['high_f'] = day['high']['fahrenheit'] + "°F"
                    WU['fc'][i]['high_c'] = day['high']['celsius'] + "°C"
                    WU['fc'][i]['low_f'] = day['low']['fahrenheit'] + "°F"
                    WU['fc'][i]['low_c'] = day['low']['celsius'] + "°C"
                    WU['fc'][i]['icon'] = day['icon']
                    if (WU['fc'][i]['icon'] == "chancerain") :
                        WU['fc'][i]['icon'] = "poss rain"
                    elif (WU['fc'][i]['icon'] == "partlycloudy") :
                        WU['fc'][i]['icon'] = "partly cloudy"
                    elif (WU['fc'][i]['icon'] == "mostlycloudy") :
                        WU['fc'][i]['icon'] = "mostly cloudy"
                    elif (WU['fc'][i]['icon'] == "chanceflurries") :
                        WU['fc'][i]['icon'] = "poss flurries"
                    elif (WU['fc'][i]['icon'] == "chancesleet") :
                        WU['fc'][i]['icon'] = "poss sleet"
                    elif (WU['fc'][i]['icon'] == "chancesnow") :
                        WU['fc'][i]['icon'] = "poss snow"
                    elif (WU['fc'][i]['icon'] == "chancetstorms") :
                        WU['fc'][i]['icon'] = "poss T-storms"
                    elif (WU['fc'][i]['icon'] == "mostlysunny") :
                        WU['fc'][i]['icon'] = "mostly sunny"
                    elif (WU['fc'][i]['icon'] == "partlysunny") :
                        WU['fc'][i]['icon'] = "mostly sunny"
                    elif (WU['fc'][i]['icon'] == "tstorms") :
                        WU['fc'][i]['icon'] = "T-storms"
                    WU['fc'][i]['icon_url'] = day['icon_url']
                    i = i + 1
                    if i > 3 :
                        break
                i = 0
                WU['fctxt'] = [dict(), dict(), dict(), dict(), dict(), dict(), dict(), dict()]
                for day in fc['txt_forecast']['forecastday'] :
                    WU['fctxt'][i]['fcttext'] = day['fcttext']
                    WU['fctxt'][i]['fcttext_metric'] = day['fcttext_metric']
                    i = i + 1
                    if i > 7 :
                        break
                status = 3
                sp = json.loads(r.data.decode('utf-8'))['sun_phase']
                WU['sunrise'] = '%s:%s AM' % (sp['sunrise']['hour'], sp['sunrise']['minute'])
                WU['sunset'] = '%s:%s PM' % (str(int(sp['sunset']['hour']) - 12), sp['sunset']['minute'])
                status = 4
                mp = json.loads(r.data.decode('utf-8'))['moon_phase']
                WU['ageOfMoon'] = int(mp['ageOfMoon'])
                # Sometimes the moonrise comes across as null.  Handle it gracefully
                if mp['moonrise']['hour'] == "" :
                    WU['moonrise'] = "N/A"
                else :
                    x = int(mp['moonrise']['hour'])
                    if x >= 12 :
                        ampm = "PM"
                    else :
                        ampm = "AM"
                    if x > 12 : # after noon
                        x = x - 12
                    elif x == 0 : # midnight
                        x = 12
                    WU['moonrise'] = '%s:%s %s' % (x, mp['moonrise']['minute'], ampm)
                # Sometimes the moonset comes across as null.  Handle it gracefully
                if mp['moonset']['hour'] == "" :
                    WU['moonset'] = "N/A"
                else :
                    x = int(mp['moonset']['hour'])
                    if x > 12 :
                        x = x - 12
                        ampm = "PM"
                    else :
                        ampm = "AM"
                    WU['moonset'] = '%s:%s %s' % (x, mp['moonset']['minute'], ampm)
                status = 5
                al = json.loads(r.data.decode('utf-8'))['alerts']
                WU['alerts'] = []
                for alert in al :
                    WU['alerts'].append(alert['message'])
                return True
            else :
                i = i + 1
                WGErrorPrint("GetWeatherData", PWS +
                                " data not newer than last weather data.  Calls Today = " +
                                str(WU_Num_Calls_Made_Today))
        except :
            i = i + 1
            WGErrorPrint("GetWeatherData", "Weather Collection Error #1 (PWS = " + PWS +
                            ", status = " + str(status) + ", Calls today = " +
                            str(WU_Num_Calls_Made_Today) + ")")
            continue # Try the next closest 
    return False # didn't find any newer PWS
