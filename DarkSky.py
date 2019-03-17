#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018-2019, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with DarkSky.net weather data
#

DarkSky_version = "1.00"

import urllib3
import json
import pprint
import datetime
from WGHelper import *

# WeatherUnderground - requires an account
from DSAccountSettings import *

wind_directions = ["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
daynames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def MoonPhaseURL() :
    return "https://www.wunderground.com/graphics/moonpictsnew/"
    
###############################################################################
#
# Get weather data from WeatherUnderground
#
def GetWeatherData(DS) :
    mintemps = [999, 999, 999, 999, 999, 999, 999]
    maxtemps = [-999, -999, -999, -999, -999, -999, -999]
    weathers = ["NA", "NA", "NA", "NA", "NA", "NA", "NA"]
    fcicons = ["NA", "NA", "NA", "NA", "NA", "NA", "NA"]
    
    try:
        status = 0
        pm = urllib3.PoolManager()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = pm.request('GET', 'https://api.darksky.net/forecast/' +
                        DS_API_KEY + '/' +
                        DS_Lat + ',' + DS_Lon +
                        '?EXCLUDE=[minutely,hourly]')
        status = 1
        co = json.loads(r.data.decode('utf-8'))
        DS['observation_time'] = str(datetime.datetime.fromtimestamp(co['currently']['time']).strftime('Upd: %Y-%m-%d %H:%M:%S'))
        DS['weather'] = co['currently']['summary']
        DS['temp_f'] = int(round(co['currently']['temperature'], 0))
        DS['relative_humidity'] = str(int(co['currently']['humidity']*100))
        DS['wind_dir'] = wind_directions[int(((co['currently']['windBearing']/22.5)+.5) % 16)]
        DS['wind_mph'] = co['currently']['windSpeed']
        DS['wind_gust_mph'] = co['currently'].get('windGust', 0)
        DS['pressure_in'] = str(round(co['currently']['pressure'] / 33.8639, 2))
        DS['windchill'] = co['currently']['apparentTemperature']
        DS['visibility_mi'] = co['currently'].get('visibility', 0)
        # DS['precip_today_in'] = 0                                          #### Fix this!
        status = 2
        i = 0
        DS['fctxt'] = [dict(), dict(), dict(), dict(), dict(), dict(), dict(), dict()]
        Today = datetime.datetime.today()
        
        for fcperiod in co['daily']['data'] :
            fcday = datetime.datetime.fromtimestamp(fcperiod['time'])
            index = fcday.weekday()
            mintemps[index] = fcperiod['temperatureMin']
            maxtemps[index] = fcperiod['temperatureMax']
            weathers[index] = fcperiod['icon']
            if weathers[index].startswith('partly-cloudy') :
                weathers[index] = 'partly cloudy'
            if weathers[index].startswith('clear') :
                weathers[index] = 'clear'
            fcicons[index] = fcperiod['icon']
            DS['fctxt'][i]['fcttext'] = fcperiod['summary']
            # WGTracePrint("Weekday = " + str(index) + ", mintemp = " + str(mintemps[index]) + ", maxtemp = " +
            #    str(maxtemps[index]) + ", weather = " + weathers[index])
            i = i + 1
            if i > 3 :
                break

        i = 0
        day = Today.weekday()
        DS['fc'] = [dict(), dict(), dict(), dict()]
        while True :
            DS['fc'][i] = dict()
            DS['fc'][i]['name'] = daynames[day]
            DS['fc'][i]['high_f'] = str(int(round(maxtemps[day], 0))) + "°F"
            DS['fc'][i]['low_f'] = str(int(round(mintemps[day], 0))) + "°F"
            DS['fc'][i]['icon'] = weathers[day]
            DS['fc'][i]['icon_url'] = fcicons[day] + ".gif"
            day = day + 1
            if day > 6 :
                day = 0
            i = i + 1
            if i > 3 :
                break
        status = 3
        DS['sunrise'] = str(datetime.datetime.fromtimestamp(co['daily']['data'][0]['sunriseTime']).strftime('%I:%M %p'))
        DS['sunset'] = str(datetime.datetime.fromtimestamp(co['daily']['data'][0]['sunsetTime']).strftime('%I:%M %p'))
        status = 4
        DS['ageOfMoon'] = int(round(28 * co['daily']['data'][0]['moonPhase'], 0))
        
        try :
            status = 5
            risetime = ["0", "0"]
            settime = ["0", "0"]
            r = pm.request('GET', 'https://api.usno.navy.mil/rstt/oneday?tz=-5&date=today&coords=' +
                            DS_Lat + ',' + DS_Lon )
            mo = json.loads(r.data.decode('utf-8'))['moondata']
            for phen in mo :
                if phen['phen'] == "R" :
                    risetime = phen['time'].split(':')
                else :
                    if phen['phen'] == "S" :
                        settime = phen['time'].split(':')
        except :
            WGErrorPrint("GetWeatherData", "Failed to get moon data from api.usno.navy.mil")
        x = int(risetime[0])
        if x >= 12 :
            ampm = "PM"
        else :
            ampm = "AM"
        if x > 12 : # after noon
            x = x - 12
        elif x == 0 : # midnight
            x = 12
        DS['moonrise'] = '%s:%s %s' % (x, risetime[1], ampm)
        x = int(settime[0])
        if x > 12 :
            x = x - 12
            ampm = "PM"
        else :
            ampm = "AM"
        DS['moonset'] = '%s:%s %s' % (x, settime[1], ampm)
            
        status = 6
        DS['alerts'] = []                                              # Fix this!
        for alert in co.get('alerts', []) :
            DS['alerts'].append(alert['description'])
        return True
    except :
        WGErrorPrint("GetWeatherData", "Weather Collection Error #1 (status = " +
                        str(status) + ")")
    return False
