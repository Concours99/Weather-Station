# pylint: disable=R0914
# pylint: disable=W0702
# pylint: disable=R0912
# pylint: disable=R0915

"""Helper module to interface with DarkSky weather service."""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018-2019, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with DarkSky.net weather data
#
import datetime
import json
import urllib3
import ephem
import sys
from wg_helper import wg_error_print
from wg_helper import wg_trace_print
# This will contain your personal DarkSky key, etc.
from dark_sky_account_settings import DS_API_KEY
from dark_sky_account_settings import DS_LAT
from dark_sky_account_settings import DS_LON

DARKSKY_VERSION = "1.01"

TRACE = False

def moonphaseurl():
    """What is the URL directory of the moon phase graphics?"""
    return "https://www.wunderground.com/graphics/moonpictsnew/"

###############################################################################
#
# Get weather data from WeatherUnderground
#
def getweatherdata(dsd):
    """Return current weather data in a structure weather.py expects"""
    mintemps = [999, 999, 999, 999, 999, 999, 999]
    maxtemps = [-999, -999, -999, -999, -999, -999, -999]
    weathers = ["NA", "NA", "NA", "NA", "NA", "NA", "NA"]
    fcicons = ["NA", "NA", "NA", "NA", "NA", "NA", "NA"]
    wind_directions = ["N", "NNE", "NE", "ENE",
                       "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW",
                       "W", "WNW", "NW", "NNW"]
    daynames = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]

    try:
        status = 0
        pman = urllib3.PoolManager()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        ret = pman.request('GET', 'https://api.darksky.net/forecast/' +
                           DS_API_KEY + '/' +
                           DS_LAT + ',' + DS_LON +
                           '?EXCLUDE=[minutely,hourly]')
        status = 1
        curr = json.loads(ret.data.decode('utf-8'))
        dsd['observation_time'] = str(datetime.datetime.fromtimestamp(curr['currently']['time'])
                                      .strftime('Upd: %Y-%m-%d %H:%M:%S'))
        dsd['weather'] = curr['currently']['summary']
        dsd['temp_f'] = int(round(curr['currently']['temperature'], 0))
        dsd['relative_humidity'] = str(int(curr['currently']['humidity']*100))
        dsd['wind_dir'] = wind_directions[int(((curr['currently']['windBearing']/22.5)+.5) % 16)]
        dsd['wind_mph'] = curr['currently']['windSpeed']
        dsd['wind_gust_mph'] = curr['currently'].get('windGust', 0)
        dsd['pressure_in'] = str(round(curr['currently']['pressure'] / 33.8639, 2))
        dsd['windchill'] = curr['currently']['apparentTemperature']
        dsd['visibility_mi'] = curr['currently'].get('visibility', 0)
        # dsd['precip_today_in'] = 0                                          #### Fix this!
        status = 2
        i = 0
        dsd['fctxt'] = [dict(), dict(), dict(), dict(), dict(), dict(), dict(), dict()]
        today = datetime.datetime.today()

        for fcperiod in curr['daily']['data']:
            fcday = datetime.datetime.fromtimestamp(fcperiod['time'])
            index = fcday.weekday()
            mintemps[index] = fcperiod['temperatureMin']
            maxtemps[index] = fcperiod['temperatureMax']
            weathers[index] = fcperiod['icon']
            if weathers[index].startswith('partly-cloudy'):
                weathers[index] = 'partly cloudy'
            if weathers[index].startswith('clear'):
                weathers[index] = 'clear'
            fcicons[index] = fcperiod['icon']
            dsd['fctxt'][i]['fcttext'] = fcperiod['summary']
            wg_trace_print("Weekday = " + str(index) + ", mintemp = " +
                           str(mintemps[index]) + ", maxtemp = " +
                           str(maxtemps[index]) + ", weather = " +
                           weathers[index], TRACE)
            i = i + 1
            if i > 3:
                break

        i = 0
        day = today.weekday()
        dsd['fc'] = [dict(), dict(), dict(), dict()]
        while True:
            dsd['fc'][i] = dict()
            dsd['fc'][i]['name'] = daynames[day]
            dsd['fc'][i]['high_f'] = str(int(round(maxtemps[day], 0))) + "°F"
            dsd['fc'][i]['low_f'] = str(int(round(mintemps[day], 0))) + "°F"
            dsd['fc'][i]['icon'] = weathers[day]
            dsd['fc'][i]['icon_url'] = fcicons[day] + ".gif"
            day = day + 1
            if day > 6:
                day = 0
            i = i + 1
            if i > 3:
                break
        status = 3
        dsd['sunrise'] = str(datetime.datetime.fromtimestamp(
            curr['daily']['data'][0]['sunriseTime'])
                             .strftime('%I:%M %p'))
        dsd['sunset'] = str(datetime.datetime.fromtimestamp(
            curr['daily']['data'][0]['sunsetTime'])
                            .strftime('%I:%M %p'))
        status = 4
        dsd['ageOfMoon'] = int(round(28 * curr['daily']['data'][0]['moonPhase'], 0))

        status = 5
        risetime = ["0", "0"]
        settime = ["0", "0"]
        ephem.Moon()
        obs_loc = ephem.Observer()
        obs_loc.lat = DS_LAT
        obs_loc.lon = DS_LON
        obs_loc.date = datetime.datetime.utcnow()
        moon_rise = ephem.localtime(obs_loc.next_rising(ephem.Moon()))
        if moon_rise.day == datetime.datetime.now().day:
            risetime = (str(ephem.localtime(obs_loc.next_rising(ephem.Moon())))
                        .split(' ')[1].split(':'))
        else:
            moon_rise = ephem.localtime(obs_loc.previous_rising(ephem.Moon()))
            if moon_rise.day == datetime.datetime.now().day:
                risetime = (str(ephem.localtime(obs_loc.previous_rising(ephem.Moon())))
                            .split(' ')[1].split(':'))
            else:
                risetime = "NA"
        moon_set = ephem.localtime(obs_loc.next_setting(ephem.Moon()))
        if moon_set.day == datetime.datetime.now().day:
            settime = (str(ephem.localtime(obs_loc.next_setting(ephem.Moon())))
                       .split(' ')[1].split(':'))
        else:
            moon_set = ephem.localtime(obs_loc.previous_setting(ephem.Moon()))
            if moon_set.day == datetime.datetime.now().day:
                settime = (str(ephem.localtime(obs_loc.previous_setting(ephem.Moon())))
                           .split(' ')[1].split(':'))
            else:
                settime = "NA"
        # wg_trace_print("moon rise " + str(risetime), True)
        if risetime != "NA":
            rtime = int(risetime[0])
            if rtime >= 12: # after noon
                ampm = "PM"
            else:
                ampm = "AM"
            if rtime > 12: # after noon
                rtime = rtime - 12
            elif rtime == 0: # midnight
                rtime = 12
            dsd['moonrise'] = '%s:%s %s' % (rtime, risetime[1], ampm)
        else:
            dsd['moonrise'] = risetime
        # wg_trace_print("moon set " + str(settime), True)
        if settime != "NA":
            stime = int(settime[0])
            if stime >= 12:
                stime = stime - 12
                ampm = "PM"
            else:
                ampm = "AM"
            if stime > 12: # after noon
                stime = stime - 12
            elif stime == 0: # midnight
                stime = 12
            dsd['moonset'] = '%s:%s %s' % (stime, settime[1], ampm)
        else:
            dsd['moonset'] = settime

        status = 6
        dsd['alerts'] = []                                              # Fix this!
        for alert in curr.get('alerts', []):
            dsd['alerts'].append(alert['description'])
        return True
    except:
        wg_error_print("GetWeatherData",
                       "Weather Collection Error #1 (status = " +
                       str(status) + ") " +
                       "(Exc type = " + str(sys.exc_info()[0]) + ") " +
                       "(Exc value = " + str(sys.exc_info()[1]) + ")")
    return False
