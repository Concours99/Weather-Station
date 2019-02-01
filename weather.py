#!/usr/bin/python3
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Portions Copyright (c) 2014 Jim Kemp <kemp.jim@gmail.com>
# Majority Copyright (c) 2018 Wayne Geiser <wayne@geiserweb.com>

#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:

#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
### END LICENSE

""" Fetches weather reports WeatherUnderground.com for display on small screens."""

__version__ = "v1.04"
TRACE = False       # write tracing lines to log file
CONTROL_LOG = True  # write lines to show control functions
ALERT = True        # For testing purposes, don't send text alerts

# Config for climate control functions
floor_temp_differential = 3

WINDOWS_OS = 0
RASPBERRY_PI = 1
RUNNING_ON = RASPBERRY_PI # What environment is this running on?

DISPLAY_SMALL = 0
DISPLAY_SMALL_WIDTH = 656
DISPLAY_SMALL_HEIGHT = 416
DISPLAY_LARGE = 1
DISPLAY_LARGE_WIDTH = 800
DISPLAY_LARGE_HEIGHT = 600
DISPLAY_WIDE = 2
DISPLAY_WIDE_WIDTH = 800
DISPLAY_WIDE_HEIGHT = 480
# Configure here
DISPLAY_SIZE = DISPLAY_WIDE # Large or small display / window
DISPLAY_WIDTH = DISPLAY_WIDE_WIDTH
DISPLAY_HEIGHT = DISPLAY_WIDE_HEIGHT

UNITS_IMPERIAL = 0
UNITS_METRIC = 1
UNITS = UNITS_IMPERIAL # Metric or Imperial units

# Misc constants
COLOR_BLACK = (0, 0, 0)
COLOR_BLUE = (100,149,237)
COLOR_RED = (220,20,60)
COLOR_WHITE = (255, 255, 255)
COLOR_GREY = (128, 128, 128)

COLOR_BACKGROUND = COLOR_BLACK
COLOR_TEXT_NORMAL = COLOR_WHITE
COLOR_TEXT_RISING = COLOR_RED
COLOR_TEXT_FALLING = COLOR_BLUE

FONT_NORMAL = "FreeSans"
FONT_LOC_ON_RASPBERRY_PI = "/usr/share/fonts/truetype/freefont"
TEXT_HEIGHT_SMALL = 0.06

RUNNING_LOC = "./"

TEMP_DEFAULT = 0.0
BARO_DEFAULT = 0.0
HUMID_DEFAULT = 0

# Control tabs
TAB_LABELS = ["Weather", "Almanac", "Alert", "History", "Details"]
TAB_WEATHER = 0
TAB_ALMANAC = 1
TAB_ALERT   = 2
TAB_HISTORY = 3
TAB_DETAILS = 4
# definition of the tab rectangles for button presses
TAB_BUTTONS = [[0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0]]
TAB_LAST = TAB_DETAILS

#definitions of the forecast rectangles for button presses
FORECAST_BUTTONS = [[0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [0, 0, 0, 0]]
# Drawing specs
BORDER_WIDTH = 5

FFC_State = {'beenhere' : False,    # State variable to know when we've
                'fmode' : -1,       # here before and what to return the
                'temp' : -1,
                'hold' : -1}        # thermostat values to that we have changed

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

###############################################################################
#   Raspberry Pi Weather Display
#   By: Jim Kemp    10/25/2014
#   And: Wayne Geiser   2018
###############################################################################
import os
import pygame
import time
import datetime
import random
from pygame.locals import *
# import calendar
import textwrap
import sys
import pickle
import string
import math

# debugging
import pprint

# weather underground
import io
from urllib.request import urlretrieve, urlopen

# My local packages
from WGHelper import *
from WGRadioThermostat import *
from WGThingSpeak import *
from WGTwilio import *
from WGWeatherUnderground import *

mode = 'w'      # Default to weather mode.

# Small LCD Display.
class SmDisplay:
    screen = None;

    ####################################################################
    #
    # Load the font from a file if I can't find it native
    #
    # Note, for efficiency, we save a loaded font under its name and size
    # so we don't have to reload it.
    #
    def LoadFont(self, fn, size) :
        # Have we already loaded (and saved) the font of this name & size?
        for f in self.fonts :
            if (f[0] == fn) and (f[1] == size) :
                return f[2]
        # I guess not, load it up
        if self.load_fonts_from_file :
            txt = fn + "Bold.ttf"
            ft = pygame.font.Font(os.path.join(FONT_LOC_ON_RASPBERRY_PI,  txt), size)
        else :
            ft = pygame.font.SysFont(fn, size, bold=1)
        # save it in the list for future calls
        self.fonts.append([fn, size, ft])
        return ft

    
    ####################################################################
    def __init__(self):
        # "Initializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        disp_no = os.getenv("DISPLAY")
        if disp_no and TRACE:
            WGTracePrint("X Display = " + str(disp_no))
    
        # Check which frame buffer drivers are available
        # Start with fbcon since directfb hangs with composite output
        # Added 'windib' and 'directx' so this will run on windows
        drivers = ['fbcon', 'directfb', 'svgalib', 'windib', 'directx']
        found = False
        for driver in drivers:
            # Make sure that SDL_VIDEODRIVER is set
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pygame.display.init()
            except pygame.error:
                if TRACE :
                    WGTracePrint("Driver: " + str(driver) + " failed.")
                continue
            found = True
            break

        if not found:
            raise Exception('No suitable video driver found!')
        
        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        if TRACE :
            WGTracePrint("Framebuffer Size: " + str(size[0]) + " x " + str(size[1]))
        if (RUNNING_ON == RASPBERRY_PI) :
           self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
        else :
            # Make a window rather than using the entire display
            if (DISPLAY_SIZE == DISPLAY_SMALL) :
                size = (DISPLAY_SMALL_WIDTH, DISPLAY_SMALL_HEIGHT)
            elif (DISPLAY_SIZE == DISPLAY_WIDE) :
                size = (DISPLAY_WIDE_WIDTH, DISPLAY_WIDE_HEIGHT)
            else :
                size = (DISPLAY_LARGE_WIDTH, DISPLAY_LARGE_HEIGHT)
            self.screen = pygame.display.set_mode(size)
            pygame.display.flip()
        # Clear the screen to start
        self.screen.fill(COLOR_BACKGROUND)        
        # Initialise font support
        pygame.font.init()
        # Render the screen
        pygame.display.update()
        self.temp = str(TEMP_DEFAULT)
        self.tempcolor = COLOR_TEXT_NORMAL
        self.feels_like = 0
        self.wind_speed = 0
        self.baro = BARO_DEFAULT
        self.barocolor = COLOR_TEXT_NORMAL
        self.wind_dir = 'S'
        self.humid = HUMID_DEFAULT
        self.humidtemp = COLOR_TEXT_NORMAL
        self.wLastUpdate = ''
        self.day = [ '', '', '', '' ]
        self.icon = [ 0, 0, 0, 0 ]
        self.rain = [ '', '', '', '' ]
        self.forecastdetails = [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ']
        self.temps = [ ['',''], ['',''], ['',''], ['',''] ]
        self.sunrise = '7:00 AM'
        self.sunset = '8:00 PM'
        # Remember min and max temperatures
        self.max_temps = [0, 0, 0, 0, 0, 0, 0]
        self.min_temps = [0, 0, 0, 0, 0, 0, 0]
        self.rainfall = [0, 0, 0, 0, 0, 0, 0]
        self.curr_day = int(time.strftime("%w"))
        # Remember if we are loading fonts from a file
        fonts = pygame.font.get_fonts()
        if (str(fonts[0]) == "None") :
            self.load_fonts_from_file = True
        else :
            self.load_fonts_from_file = False
        self.fonts = []
        self.alerts_sent = []

        if (DISPLAY_SIZE == DISPLAY_SMALL) :
            self.xmax = DISPLAY_SMALL_WIDTH - 35
            self.ymax = DISPLAY_SMALL_HEIGHT - 5
            self.scaleIcon = True       # Weather icons need scaling.
            self.iconScale = 1.5        # Icon scale amount.
            self.subwinTh = 0.05        # Sub window text height
            self.tmdateTh = 0.100       # Time & Date Text Height
            self.tmdateSmTh = TEXT_HEIGHT_SMALL
            self.tmdateYPos = 10        # Time & Date Y Position
            self.tmdateYPosSm = 18      # Time & Date Y Position Small
        elif (DISPLAY_SIZE == DISPLAY_WIDE) :
            self.xmax = DISPLAY_SMALL_WIDTH - 35 # extra room on the side for buttons
            self.ymax = DISPLAY_WIDE_HEIGHT - 5
            self.scaleIcon = False      # No icon scaling needed.
            self.iconScale = 1.0
            self.subwinTh = 0.04        # Sub window text height
            self.tmdateTh = 0.11       # Time & Date Text Height
            self.tmdateSmTh = 0.06
            self.tmdateYPos = 1         # Time & Date Y Position
            self.tmdateYPosSm = 8       # Time & Date Y Position Small
        else : # DISPLAY_LARGE
            self.xmax = DISPLAY_LARGE_WIDTH - 35
            self.ymax = DISPLAY_LARGE_HEIGHT - 5
            self.scaleIcon = False      # No icon scaling needed.
            self.iconScale = 1.0
            self.subwinTh = 0.065       # Sub window text height
            self.tmdateTh = 0.125       # Time & Date Text Height
            self.tmdateSmTh = 0.075
            self.tmdateYPos = 1         # Time & Date Y Position
            self.tmdateYPosSm = 8       # Time & Date Y Position Small
 

    ####################################################################
    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    ####################################################################
    #
    # Draw the tab rectangles on the left hand side of the screen.
    # arguments - 
    #   which - which tab is currently being displayed (see the top of the
    #           file for enumerated list of tabs)
    def draw_tabs(self, which) :
        button_height = (self.ymax*0.15)-2 # 15% of screen height
        p_top = 2
        p_bottom = p_top + button_height
        p_left = self.xmax
        p_right = DISPLAY_WIDTH-3
        button_width = (p_right-p_left)
        # If we have alerts, draw the outline in red
        if len(self.alerts_sent) == 0 :
            color = COLOR_WHITE
        else :
            color = COLOR_RED
        # draw the top line
        if (which == 0) :
             pygame.draw.line(self.screen, color, (p_left+3, p_top), (p_right+2, p_top),
                                BORDER_WIDTH)
        else :
             pygame.draw.line(self.screen, COLOR_GREY, (p_left+3, p_top), (p_right+2, p_top),
                                BORDER_WIDTH)
        # draw the left, right, and bottom of each of the buttons
        for i in range(TAB_LAST + 1) :
            # remember the tab rectangle that we can use as a button
            TAB_BUTTONS[i][0] = p_left
            TAB_BUTTONS[i][1] = p_top
            TAB_BUTTONS[i][2] = button_width
            TAB_BUTTONS[i][3] = button_height
            if (which == i) : # active tab
                lc = COLOR_TEXT_NORMAL
                lc2 = COLOR_BACKGROUND
                lc3 = color
            else :
                lc = COLOR_GREY
                lc2 = color
                lc3 = COLOR_GREY
            pygame.draw.line(self.screen, lc2, (p_left, p_top+3), (p_left, p_bottom-3), BORDER_WIDTH) # left
            pygame.draw.line(self.screen, lc3, (p_right, p_top+3), (p_right, p_bottom), BORDER_WIDTH) # right
            if (which == i) :     # redraw the top as it should have been white
              pygame.draw.line(self.screen, color, (p_left+3, p_top), (p_right+2, p_top), BORDER_WIDTH)
            pygame.draw.line(self.screen, lc3, (p_left+3, p_bottom), (p_right+2, p_bottom), BORDER_WIDTH) # bottom
            p_top = p_top + button_height
            p_bottom = p_bottom + button_height
            font = self.LoadFont(FONT_NORMAL, int(self.ymax*TEXT_HEIGHT_SMALL))
            txt = font.render(TAB_LABELS[i], True, lc)
            (tx,ty) = txt.get_size()
            self.screen.blit(txt, (self.xmax+BORDER_WIDTH, self.ymax*(0.15*(i+1))-BORDER_WIDTH-ty))
                    
    ####################################################################
    #
    # Draw the outline around the right hand side of the screen.
    def draw_screen_outline(self) :
        # If we have alerts, draw the outline in red
        if len(self.alerts_sent) == 0 :
            color = COLOR_WHITE
        else :
            color = COLOR_RED
        # Draw Screen Border
        pygame.draw.line(self.screen, color, (0, 2), (self.xmax+2, 2), BORDER_WIDTH) # top border
        pygame.draw.line(self.screen, color, (2,2), (2,self.ymax), BORDER_WIDTH) # left border
        pygame.draw.line(self.screen, color, (0,self.ymax+2), (self.xmax+2,self.ymax+2), BORDER_WIDTH) # Bottom border
        pygame.draw.line(self.screen, color, (self.xmax,2),(self.xmax,self.ymax), BORDER_WIDTH) # right border
        # Add Weather Underground logo to bottom right hand corner of the screen
        icon = pygame.image.load(os.path.join(RUNNING_LOC, "WU-logo-sm.gif"))
        (ix,iy) = icon.get_size()
        self.screen.blit(icon, (self.xmax, self.ymax-iy))
        # Display version string
        font = self.LoadFont(FONT_NORMAL, int(self.ymax*TEXT_HEIGHT_SMALL))
        txt = font.render(__version__, True, COLOR_TEXT_NORMAL)
        (tx,ty) = txt.get_size()
        self.screen.blit(txt, (self.xmax+ix, self.ymax-ty))

    ####################################################################
    #
    # Save interesting stuff to disk
    def save_data(self) :
        pickle.dump(self.max_temps, open("max_temps.p", "wb"))
        pickle.dump(self.min_temps, open("min_temps.p", "wb"))
        pickle.dump(self.rainfall, open("rainfall.p", "wb"))
   
    ####################################################################
    #
    # Restore interesting stuff from disk
    def restore_data(self) :
        try :
            self.max_temps = pickle.load(open("max_temps.p", "rb"))
            self.min_temps = pickle.load(open("min_temps.p", "rb"))
            self.rainfall = pickle.load(open("rainfall.p", "rb"))
        except :
            WGErrorPrint("restore_data", "Restore failed")
    
    ####################################################################
    #
    # Draw the time and date at the top of the screen
    def draw_time_and_date(self) :
        # If we have alerts, draw the outline in red
        if len(self.alerts_sent) == 0 :
            color = COLOR_WHITE
        else :
            color = COLOR_RED
        pygame.draw.line(self.screen, color, (2,self.ymax*0.15),(self.xmax,self.ymax*0.15), BORDER_WIDTH)

        # Time & Date
        font = self.LoadFont(FONT_NORMAL, int(self.ymax*self.tmdateTh))
        sfont = self.LoadFont(FONT_NORMAL, int(self.ymax*self.tmdateSmTh))

        tm1 = time.strftime( "%a, %b %d   %I:%M", time.localtime() )    # date, hours, minutes
        tm2 = time.strftime( "%S", time.localtime() )                   # seconds
        tm3 = time.strftime( " %p", time.localtime() )                  # am/pm

        rtm1 = font.render(tm1, True, COLOR_TEXT_NORMAL)
        (tx1,ty1) = rtm1.get_size()
        rtm2 = sfont.render(tm2, True, COLOR_TEXT_NORMAL)
        (tx2,ty2) = rtm2.get_size()
        rtm3 = font.render(tm3, True, COLOR_TEXT_NORMAL)
        (tx3,ty3) = rtm3.get_size()

        tp = self.xmax / 2 - (tx1 + tx2 + tx3) / 2
        self.screen.blit(rtm1, (tp, self.tmdateYPos))
        self.screen.blit(rtm2, (tp+tx1+3, self.tmdateYPosSm))
        self.screen.blit(rtm3, (tp+tx1+tx2, self.tmdateYPos))

        if (self.curr_day != int(time.strftime("%w"))) : # it's a new day!
            self.curr_day = int(time.strftime("%w"))
            self.max_temps[self.curr_day] = 0
            self.min_temps[self.curr_day] = 0
            self.rainfall[self.curr_day] = 0
            self.save_data()

    ####################################################################
    #
    #   Saves a URL file to a disk file to avoid Internet calls later
    def SaveURLtoFile(self, URL, fil_name) :
        # create the icons directory if it doesn't exist
        dir = RUNNING_LOC + 'icons'
        if not os.path.exists(dir) :
            os.makedirs(dir)
        fil = dir + "/" + fil_name + ".gif"
        if TRACE :
            WGTracePrint(URL)
            WGTracePrint(fil)
        # Does it already exist?
        if (os.path.isfile(fil)) :
            # If so, don't do anything and return the filename
            return fil
        # If not, save the URL to a disk file
        urlretrieve(URL, fil)
        # and return the fileneme
        return fil
    
    ####################################################################
    #
    # Get data from local station via weather underground
    def UpdateWeather(self) :
        if TRACE :
            WGTracePrint("in UpdateWeather")
        if (self.temp == '??') :
            oldtemp = TEMP_DEFAULT # keep it from crashing
        else :
            oldtemp = float(self.temp)
        oldbaro = float(self.baro)
        oldhumid = float(self.humid)

        WeatherData = dict()
        RetVal = GetWeatherData(WeatherData)
        if not RetVal :
            self.temp = '??'
            self.wLastUpdate = ''
            WGErrorPrint("UpdateWeather", "Unable to get Weather Data")
            return

        # Handle weather alerts
        try :
            if len(WeatherData['alerts']) == 0 : # No alerts to deal with, clear the saved list
                self.alerts_sent = []
            else :
                for alert in WeatherData['alerts'] :
                    # check to see if we've already sent this one
                    send_it = True
                    for already_sent in self.alerts_sent :
                        if already_sent != WeatherData['alerts'].pop :
                            send_it = False
                            break
                    if send_it :
                        alert_msg = 'Alert: %s' % (alert)
                        if ALERT :
                            SendText(alert_msg)
                        # Update alert list after sending in case there was an error in sending
                        # it.  That way, we'll try to send it again next time.
                        self.alerts_sent.append(alert)
        except :
           WGErrorPrint("UpdateWeather", "Alert Exception")
           pp = pprint.PrettyPrinter(indent=4)
           pp.pprint(WeatherData['alerts'])
        
        try :
            if (WeatherData['observation_time'] != self.wLastUpdate) :
                self.wLastUpdate = WeatherData['observation_time']
                if TRACE :
                    WGTracePrint("New Weather " + self.wLastUpdate)
                if (UNITS == UNITS_IMPERIAL) :
                    self.temp = "%d" % (WeatherData['temp_f'])
                    self.rainfall[self.curr_day] = WeatherData['precip_today_in']
                else :
                    self.temp = "%d" % (WeatherData['temp_c'])
                    self.rainfall[self.curr_day] = "%f" % (WeatherData['precip_today_metric'])
                if TRACE :
                    WGTracePrint('temp is ' + self.temp)
                if (self.max_temps[self.curr_day] == 0) and (self.min_temps[self.curr_day] == 0) :
                    self.min_temps[self.curr_day] = float(self.temp)
                    self.max_temps[self.curr_day] = float(self.temp)
                    self.save_data()
                # if the value changed from last time, what color should we now display?
                if (oldtemp == float(TEMP_DEFAULT)) :
                    self.tempcolor = COLOR_TEXT_NORMAL
                elif (float(self.temp) > oldtemp) :
                    self.tempcolor = COLOR_TEXT_RISING
                    if (float(self.temp) > self.max_temps[self.curr_day]) :
                        self.max_temps[self.curr_day] = float(self.temp) # save the new max
                        self.save_data()
                elif (float(self.temp) < oldtemp) :
                    self.tempcolor = COLOR_TEXT_FALLING
                    if (float(self.temp) < self.min_temps[self.curr_day]) :
                        self.min_temps[self.curr_day] = float(self.temp) # save the new min
                        self.save_data()
                self.curr_cond = WeatherData['weather']
                if (UNITS == UNITS_IMPERIAL) :
                    self.feels_like = "%d" % (int(round(float(WeatherData['feelslike_f']))))
                else :
                    self.feels_like = "%d" % (int(round(float(WeatherData['feelslike_c']))))
                if (UNITS == UNITS_IMPERIAL) :
                    self.wind_speed = "%d" % (int(WeatherData['wind_mph']))
                else :
                    self.wind_speed = "%d" % (int(WeatherData['wind_kph']))
                if (UNITS == UNITS_IMPERIAL) :
                    self.baro = WeatherData['pressure_in']
                else :
                    self.baro = WeatherData['pressure_mb']
                # if the value changed from last time, what color should we now display?
                if (oldbaro == BARO_DEFAULT) :
                    self.barocolor = COLOR_TEXT_NORMAL
                elif (float(self.baro) > oldbaro) :
                    self.barocolor = COLOR_TEXT_RISING
                elif (float(self.baro) < oldbaro) :
                    self.barocolor = COLOR_TEXT_FALLING
                self.wind_dir = WeatherData['wind_dir']
                self.humid = WeatherData['relative_humidity'].rstrip('%')
                if TRACE :
                    WGTracePrint("Sending WU Data to ThingSpeak")
                # Tell ThingSpeak what the temperature, humidity, & barometric pressure is
                ThingSpeakSendFloatNum(TS_WEATHER_CHAN, 4, "1", self.temp, "2", self.baro, "3",
                    self.humid, "4", WeatherData['pws'], TRACE)
                # if the value changed from last time, what color should we now display?
                if (oldhumid == HUMID_DEFAULT) :
                    self.humidcolor = COLOR_TEXT_NORMAL
                elif (float(self.humid) > oldhumid) :
                    self.humidcolor = COLOR_TEXT_RISING
                elif (float(self.humid) < oldhumid) :
                    self.humidcolor = COLOR_TEXT_FALLING
                if (UNITS == UNITS_IMPERIAL) :
                    self.vis = WeatherData['visibility_mi']
                else :
                    self.vis = WeatherData['visibility_km']
                if (UNITS == UNITS_IMPERIAL) :
                    self.gust = '%s' % (int(round(float(WeatherData['wind_gust_mph']))))
                else :
                    self.gust = '%s' % (int(round(float(WeatherData['wind_gust_kph']))))
                if TRACE :
                    WGTracePrint("forecast data")
                    pp = pprint.PrettyPrinter(indent=4)
                    pp.pprint(WeatherData['fc'])
                    pp.pprint(WeatherData['fctxt'])
                i = 0
                for day in WeatherData['fc'] :
                    self.day[i] = day['name']
                    if (UNITS == UNITS_IMPERIAL) :
                        self.temps[i][0] = day['high_f']
                        self.temps[i][1] = day['low_f']
                    else :
                        self.temps[i][0] = day['high_c']
                        self.temps[i][1] = day['low_c']
                    self.rain[i] = day['icon']
                    self.icon[i] = self.SaveURLtoFile(day['icon_url'], self.rain[i])
                    i = i + 1
                    if i > 3 :
                        break
                # There are two forecast details per day (day and night)
                i = 0
                for day in WeatherData['fctxt'] :
                    if (UNITS == UNITS_IMPERIAL) :
                        self.forecastdetails[i] = day['fcttext']
                    else :
                        self.forecastdetails[i] = day['fcttext_metric']
                    i = i + 1
                    if i > 7 :
                        break
                if TRACE :
                    WGTracePrint("Sun and moon data")
                self.sunrise = WeatherData['sunrise']
                self.sunset = WeatherData['sunset']
                self.moonrise = WeatherData['moonrise']
                self.moonset = WeatherData['moonset']
                s = 'moon'+str(WeatherData['ageOfMoon'])
                self.moonicon = self.SaveURLtoFile(MoonPhaseURL() + s + '.gif', s)
            else :
                self.temp = '??'
                self.wLastUpdate = ''
            if TRACE :
                WGTracePrint('temp is ' + self.temp)
        except :
            WGErrorPrint("UpdateWeather", "Weather Collection Error #2")
            self.temp = '??'
            self.wLastUpdate = ''
       
    ####################################################################
    #
    # Get data from interior data sources and update ThingSpeak
    def UpdateInsideData(self) :
        if TRACE :
            WGTracePrint("Updating inside data")
        t = RadThermGetFloat("temp", TRACE)
        if t == RadTherm_float_ERROR :
            return
        # Get the humidity from the hall thermostat
        if TRACE :
            WGTracePrint("Get thermostat humidity data")
        h = RadThermGetFloat("humidity", TRACE)
        if TRACE :
            WGTracePrint("Thermostat returned h = " + str(h))
        if h == RadTherm_float_ERROR :
            return
        ThingSpeakSendFloatNum(TS_THERM_CHAN, 2, "1", t, "2", h, " ", 0, " ", 0, TRACE)
    
    ####################################################################
    #
    # Should the furnace fan come on?  That is, is the family room temp
    # enough higher than the hallway to warrant blowing air around the
    # house?
    #
    def FurnaceFanControl(self) :
        tstat_status = RadThermStatus(TRACE)
        if 'error' in tstat_status :
            WGErrorPrint("FurnaceFanControl", "Error getting thermostat status.  Skipping thermostat control")
            return  # try again the next time
        if TRACE :
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(tstat_status)
        ht = tstat_status['temp']       # air temp
        fan = tstat_status['fmode']     # fan mode
        tmode = tstat_status['tmode']   # thermostat mode (heat?)
        hold = tstat_status['hold']     # hold?
        mode = RadThermGetInt("mode", TRACE)
        if mode == RadTherm_int_ERROR :
            return  # try again next time
        # Get the temperature from the basement sensor
        bt = ThingSpeakGetFloat(TS_BASEMENT_CHAN, "1", TRACE)
        if bt == ThingSpeak_float_ERROR :
            return # try again the next time
        bh = ThingSpeakGetFloat(TS_BASEMENT_CHAN, "2", TRACE)
        if bh == ThingSpeak_float_ERROR :
            return # try again the next time
        strret = RadThermSetStr("uma_line0", "Basement T/H: " + str(bt) + "/" + str(bh) + "%", TRACE)
        if strret == RadTherm_str_ERROR :
            WGErrorPrint("FurnaceFanControl", "Warning, unable to set user line 0 values")
            # Don't have to skip out as this isn't critical
        # Is the thermostat set to "heat" (i.e., it's "winter")?
        if tmode == TMODE_HEAT :
            # If the temperature in the basement is the right number of degrees hotter than the hallway
            if ht < (bt - floor_temp_differential) :
                # and the fan is not on
                if (fan != FAN_ON) and not FFC_State['beenhere'] :
                    # Set to Save Energy mode temporarily to get the target temp
                    intret = RadThermSetInt("mode", SAVE_ENERGY_MODE_ENABLE, TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    t = RadThermGetFloat("t_heat", TRACE)
                    # Reset Save energy mode (do this regardless of whether the "GetFloat" call
                    # worked or it'll leave the tstat in SAVE ENERGY mode)
                    intret = RadThermSetInt("mode", SAVE_ENERGY_MODE_DISABLE, TRACE)
                    if intret == RadTherm_int_ERROR or t == RadTherm_float_ERROR:
                        return # try again next time
                    FFC_State['fmode'] = fan
                    FFC_State['hold'] = hold
                    # Turn the furnace fan on
                    intret = RadThermSetInt("fmode", FAN_ON, TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    # Hold t-stat settings
                    intret = RadThermSetInt("hold", HOLD_ENABLED, TRACE)
                    if intret == RadTherm_int_ERROR :
                        # Fix anything we were successful at and leave
                        intret = RadThermSetInt("fmode", FFC_State['fmode'], TRACE)
                        return # try again next time
                    # Set temp target temperature
                    floatret = RadThermSetFloat("t_heat", t, TRACE)
                    if floatret == RadTherm_float_ERROR :
                        # Fix anything we were successful at and leave
                        intret = RadThermSetInt("hold", HOLD_DISABLED, TRACE)
                        intret = RadThermSetInt("fmode", FFC_State['fmode'], TRACE)
                        return # try again next time                         
                    FFC_State['beenhere'] = True    # do this as late as possible
                    if CONTROL_LOG :
                        WGTracePrint("Turned the furnace fan on")
            else :
                # else, if the furnace fan is on
                if (fan == FAN_ON) and FFC_State['beenhere'] :
                    # Return the thermostat to its former setting
                    intret = RadThermSetInt("fmode", FFC_State['fmode'], TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    intret = RadThermSetInt("hold", FFC_State['hold'], TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    # Set Save energy mode on and then off again to run the current program
                    intret = RadThermSetInt("mode", SAVE_ENERGY_MODE_ENABLE, TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    intret = RadThermSetInt("mode", SAVE_ENERGY_MODE_DISABLE, TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    FFC_State['beenhere'] = False
                    if CONTROL_LOG :
                        WGTracePrint("Reurned the furnace fan to previous values")
        else :
            # we're not in the heating season, figure out if we want the fan on circulate
            # if the temperature in the basement is the right number of degrees cooler than the hallway
            if (ht - floor_temp_differential) > bt :
                # and the fan is not set to circulate
                if (fan != FAN_CIRC) and not FFC_State['beenhere'] :
                    FFC_State['fmode'] = fan
                    # Turn the furnace fan to circulate
                    intret = RadThermSetInt("fmode", FAN_CIRC, TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    if CONTROL_LOG :
                        WGTracePrint("Turned the furnace fan to circulate")
                    FFC_State['beenhere'] = True
            else :
                # else, if the furnace fan is set to circulate
                if (fan == FAN_CIRC) and FFC_State['beenhere'] :
                    # return the furnace fan to its previous setting
                    intret = adThermSetInt("fmode", FFC_State['fmode'], TRACE)
                    if intret == RadTherm_int_ERROR :
                        return # try again next time
                    if CONTROL_LOG :
                        WGTracePrint("Turned the furnace fan to auto")
                    FFC_State['beenhere'] = False

    ####################################################################
    def disp_weather(self):
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)
        xmin = 2
        xmax = self.xmax
        ymin = 2
        ymax = self.ymax
        # If we have alerts, draw the outline in red
        if len(self.alerts_sent) == 0 :
            color = COLOR_WHITE
        else :
            color = COLOR_RED
        lc = COLOR_TEXT_NORMAL 
        fn = FONT_NORMAL
        
        if (UNITS == UNITS_IMPERIAL) :
            tempchar = "F"
            barpressstr = "\"Hg"
            speedstr = "mph"
        else :
            tempchar = "C"
            barpressstr = "mb"
            speedstr = "kph"
        if (int(self.temp) > 99) or (int(self.temp) < -9) :   # three digits
            tempchar = ""                           # get rid of the character for F or C

        myDisp.draw_screen_outline()
        # .15 is 15% down from the top of the screen for date/time underline
        pygame.draw.line( self.screen, color, (xmin,ymax*0.5),(xmax,ymax*0.5), BORDER_WIDTH)
        pygame.draw.line( self.screen, color, (xmax*0.25,ymax*0.5),(xmax*0.25,ymax), BORDER_WIDTH)
        pygame.draw.line( self.screen, color, (xmax*0.5,ymax*0.15),(xmax*0.5,ymax), BORDER_WIDTH)
        pygame.draw.line( self.screen, color, (xmax*0.75,ymax*0.5),(xmax*0.75,ymax), BORDER_WIDTH)
        
        # remember rectangles for button presses
        FORECAST_BUTTONS[0][0] = xmin       # left
        FORECAST_BUTTONS[1][0] = xmax*0.25
        FORECAST_BUTTONS[2][0] = xmax*0.5
        FORECAST_BUTTONS[3][0] = xmax*0.75
        # all the same top, width, and height
        for i in range(4) :
            FORECAST_BUTTONS[i][1] = ymax*0.5                       # top
            FORECAST_BUTTONS[i][2] = (xmax-xmin)*0.25               # width
            FORECAST_BUTTONS[i][3] = ymax - FORECAST_BUTTONS[i][1]  # height

        # Time and date at the top of the scrren
        myDisp.draw_time_and_date()
        # Draw tabs
        myDisp.draw_tabs(TAB_WEATHER)

        # Outside Temp
        font = self.LoadFont(fn, int(ymax*(0.5-0.15)*0.9))
        if TRACE :
            WGTracePrint('temp is ' + self.temp)
        txt = font.render(self.temp, True, self.tempcolor)
        (tx,ty) = txt.get_size()
        dfont = self.LoadFont(fn, int(ymax*(0.5-0.15)*0.5))
        dtxt = dfont.render("°" + tempchar, True, lc)
        (tx2,ty2) = dtxt.get_size()
        x = xmax*0.27 - (tx*1.02 + tx2) / 2
        self.screen.blit( txt, (x,ymax*0.15) )
        x = x + (tx*1.02)
        self.screen.blit( dtxt, (x,ymax*0.2) )

        # Conditions
        st = 0.16    # Yaxis Start Pos
        gp = 0.065   # Line Spacing Gap
        th = TEXT_HEIGHT_SMALL    # Text Height
        dh = 0.05    # Degree Symbol Height
        so = 0.01    # Degree Symbol Yaxis Offset
        xp = 0.52    # Xaxis Start Pos
        x2 = 0.78    # Second Column Xaxis Start Pos

        font = self.LoadFont(fn, int(ymax*th))
        txt = font.render( 'Feels Like:', True, lc )
        self.screen.blit( txt, (xmax*xp,ymax*st) )
        txt = font.render( self.feels_like, True, lc )
        self.screen.blit( txt, (xmax*x2,ymax*st) )
        (tx,ty) = txt.get_size()
        dfont = self.LoadFont(fn, int(ymax*dh))
        dtxt = dfont.render( "°" + tempchar, True, lc )
        self.screen.blit( dtxt, (xmax*x2+tx*1.01,ymax*(st+so)) )

        txt = font.render( 'Windspeed:', True, lc )
        self.screen.blit( txt, (xmax*xp,ymax*(st+gp*1)) )
        if (self.wind_speed == "calm") :
            txt = font.render(self.wind_speed, True, lc)
        else :
            txt = font.render( self.wind_speed + " " + speedstr, True, lc )
        self.screen.blit( txt, (xmax*x2,ymax*(st+gp*1)) )

        txt = font.render( 'Direction:', True, lc )
        self.screen.blit( txt, (xmax*xp,ymax*(st+gp*2)) )
        txt = font.render(self.wind_dir.upper(), True, lc )
        self.screen.blit( txt, (xmax*x2,ymax*(st+gp*2)) )

        txt = font.render( 'Barometer:', True, lc )
        self.screen.blit( txt, (xmax*xp, ymax*(st+gp*3)) )
        txt = font.render(self.baro, True, self.barocolor)
        self.screen.blit( txt, (xmax*x2,ymax*(st+gp*3)) )
        (tx2,ty2) = txt.get_size()
        txt = font.render(" " + barpressstr, True, lc)
        self.screen.blit(txt, (xmax*x2+tx2, ymax*(st+gp*3)) )

        txt = font.render( 'Humidity:', True, lc )
        self.screen.blit( txt, (xmax*xp,ymax*(st+gp*4)) )
        txt = font.render(self.humid, True, self.humidcolor)
        self.screen.blit( txt, (xmax*x2,ymax*(st+gp*4)) )
        (tx2,ty2) = txt.get_size()
        txt = font.render('%', True, lc)
        self.screen.blit(txt, (xmax*x2+tx2,ymax*(st+gp*4)))


        wx =    0.125           # Sub Window Centers
        wy =    0.510           # Sub Windows Yaxis Start
        th =    self.subwinTh       # Text Height
        rpth =  0.100           # Rain Present Text Height
        gp =    0.065           # Line Spacing Gap
        ro =    0.010 * xmax    # "Rain:" Text Window Offset winthin window. 
        rpl =   5.95            # Rain percent line offset.

        font = self.LoadFont(fn, int(ymax*th))
        rpfont = self.LoadFont(fn, int(ymax*rpth))

        dyi = -1
        for dy in self.day :
            # Daily forecast sub-windows
            dyi = dyi + 1
            if dyi == 0 :
                dytxt = "Today"
            else :
                dytxt = self.day[dyi]
            txt = font.render(dytxt + ':', True, lc)
            (tx,ty) = txt.get_size()
            self.screen.blit(txt, (xmax*wx*((dyi*2)+1)-tx/2, ymax*(wy+gp*0)))
            txt = font.render(self.temps[dyi][0] + ' / ' + self.temps[dyi][1], True, lc)
            (tx,ty) = txt.get_size()
            self.screen.blit(txt, (xmax*wx*((dyi*2)+1)-tx/2, ymax*(wy+gp*5)))
            txt = font.render(self.rain[dyi], True, lc)
            (tx,ty) = txt.get_size()
            self.screen.blit(txt, (xmax*wx*((dyi*2)+1)-tx/2, ymax*(wy+gp*rpl)))
            try :
                # icons have been saved to disk when we got the weather forecast/q/
                # so as to avoid continually going out on the Internet
                icon = pygame.image.load(os.path.join(RUNNING_LOC, self.icon[dyi]))
                (ix,iy) = icon.get_size()
                if self.scaleIcon:
                    icon2 = pygame.transform.scale(icon, (int(ix*1.5), int(iy*1.5)))
                    (ix,iy) = icon2.get_size()
                    icon = icon2
                if ( iy < 90 ):
                    yo = (90 - iy) / 2 
                else: 
                    yo = 0
                self.screen.blit(icon, (xmax*wx*((dyi*2)+1)-ix/2, ymax*(wy+gp*1.2)+yo))
            except :
                # nothing.  We hope it works next time
                WGErrorPrint("disp_weather", "Icon error: " + dytxt)

        # Update the display
        pygame.display.update()

    ####################################################################
    def disp_alert(self):
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)
        
        max_lines = 14 # Maximum number of lines from the alert message that will fit on screen

        myDisp.draw_screen_outline()

        # Time and date at the top of the screen
        myDisp.draw_time_and_date()
        # Draw tabs
        myDisp.draw_tabs(TAB_ALERT)

        sfont = self.LoadFont(FONT_NORMAL, int(self.ymax*self.subwinTh))
        printline = 4;

        # No alert, say so
        if len(self.alerts_sent) == 0 :
            printline = printline + 1
            txt = sfont.render("No alert!", True, COLOR_TEXT_NORMAL)
            self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        else :   
            # Just do the last alert
            i = 0
            for ln in textwrap.wrap(self.alerts_sent[len(self.alerts_sent) - 1], 50, subsequent_indent="  ") :
                printline = printline + 1
                txt = sfont.render(ln, True, COLOR_TEXT_NORMAL)
                self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
                i = i + 1
                if i == max_lines :
                    break;

        # Update the display
        pygame.display.update()

    ####################################################################
    def sPrint( self, s, font, x, l, lc ):
        f = font.render( s, True, lc )
        self.screen.blit( f, (x,self.ymax*0.075*l) )

    ####################################################################
    def disp_almanac( self, inDaylight, dayHrs, dayMins, tDaylight, tDarkness ):
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)
        xmax = self.xmax
        ymax = self.ymax
        xmin = 2
        ymin = 2
        lc = COLOR_TEXT_NORMAL 
        fn = FONT_NORMAL

        if (UNITS == UNITS_IMPERIAL) :
            tempchar = "F"
            tempvisstr = " mi"
            barpressstr = " \"Hg"
            speedstr = " mph"
        else :
            tempchar = "C"
            tempvisstr = " km"
            barpressstr = " mb"
            speedstr = " kph"
            
        myDisp.draw_screen_outline()

        # Time and date at the top of the screen
        myDisp.draw_time_and_date()
        # Draw tabs
        myDisp.draw_tabs(TAB_ALMANAC)

        sfont = self.LoadFont(FONT_NORMAL, int(self.ymax*self.tmdateSmTh))
        printline = 3
        s = "Sun Rise/Set %s / %s" % (self.sunrise, self.sunset)
        self.sPrint(s, sfont, xmax*0.05, printline, lc)

        printline = printline + 1
        s = "Daylight (Hrs:Min): %d:%02d" % (dayHrs, dayMins)
        self.sPrint( s, sfont, xmax*0.05, printline, lc )

        printline = printline + 1
        if inDaylight:
            s = "Sunset in (Hrs:Min): %d:%02d" % stot( tDarkness )
        else:
            s = "Sunrise in (Hrs:Min): %d:%02d" % stot( tDaylight )
        self.sPrint( s, sfont, xmax*0.05, printline, lc )

        printline = printline + 1
        s = self.wLastUpdate
        self.sPrint( s, sfont, xmax*0.05, printline, lc )

        printline = printline + 1
        s = "Current Cond: %s" % self.curr_cond
        self.sPrint( s, sfont, xmax*0.05, printline, lc )
        
        printline = printline + 1
        s = self.temp + "°" + tempchar + " "
        s = s + self.baro + barpressstr
        s = s + ' Wnd '
        s = s + self.wind_dir + " @ " + self.wind_speed
        if self.gust != 'N/A': 
            s = s + ' (g ' + str(self.gust) + ') '
        s = s + speedstr
        self.sPrint(s, sfont, xmax*0.05, printline, lc)

        printline = printline + 1
        s = "Visability %s" % self.vis
        s = s + tempvisstr
        self.sPrint( s, sfont, xmax*0.05, printline, lc )
        
        printline = printline + 1
        s = "Moon Rise/Set %s / %s" % (self.moonrise, self.moonset)
        self.sPrint( s, sfont, xmax*0.05, printline, lc )
       
        # Moon phase
        icon = pygame.image.load(os.path.join(RUNNING_LOC, self.moonicon))
        (ix,iy) = icon.get_size()
        self.screen.blit(icon, (xmax-ix-2, ymax-iy))

        # Update the display
        pygame.display.update()

    ####################################################################
    #
    # Min and Max temperatures for the past week (or since startup)
    def disp_history(self) :
        self.screen.fill(COLOR_BACKGROUND)
        myDisp.draw_screen_outline()
        # Time and date at the top of the scrren
        myDisp.draw_time_and_date()
        # Draw tabs
        myDisp.draw_tabs(TAB_HISTORY)

        # Display daily min and max temps
        if (UNITS == UNITS_IMPERIAL) :
            tempchar = "F"
            rainunits = "in"
        else :
            tempchar = "C"
            rainunits = "mm"
        sfont = self.LoadFont(FONT_NORMAL, int(self.ymax*self.tmdateSmTh))
        i = self.curr_day
        for j in range(7) :
            if ((self.min_temps[i] != 0) or (self.max_temps[i] != 0)) :
                s = "%s - Min: %d°%s, Max: %d°%s, Rain: %s %s" % (DAY_NAMES[i], self.min_temps[i],
                                                                    tempchar, self.max_temps[i], tempchar,
                                                                    self.rainfall[i], rainunits)
                self.sPrint(s, sfont, self.xmax*0.05, 3+j, COLOR_TEXT_NORMAL)
            i = i - 1
            if (i == -1) :
                i = 6
        
        # Update the display
        pygame.display.update()

    ####################################################################
    #
    # Detailed forecast
    #
    # Parameters:
    #   period = what day (0 = today)
    def disp_details(self, period) :
        self.screen.fill(COLOR_BACKGROUND)
        myDisp.draw_screen_outline()
        # Time and date at the top of the scrren
        myDisp.draw_time_and_date()
        # Draw tabs
        myDisp.draw_tabs(TAB_DETAILS)

        printline = 4
        sfont = self.LoadFont(FONT_NORMAL, int(self.ymax*self.subwinTh))
        txt = sfont.render(self.day[period], True, COLOR_TEXT_NORMAL)
        self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        for ln in textwrap.wrap(self.forecastdetails[period*2], 50, subsequent_indent="  ") :
            printline = printline + 1
            txt = sfont.render(ln, True, COLOR_TEXT_NORMAL)
            self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        printline = printline + 2
        ln = self.day[period] + ' Night'
        txt = sfont.render(ln, True, COLOR_TEXT_NORMAL)
        self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        for ln in textwrap.wrap(self.forecastdetails[(period*2)+1], 50, subsequent_indent="  ") :
            printline = printline + 1
            txt = sfont.render(ln, True, COLOR_TEXT_NORMAL)
            self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        
        # Update the display
        pygame.display.update()

    # Save a jpg image of the screen.
    ####################################################################
    def screen_cap( self ):
        pygame.image.save( self.screen, "screenshot.jpeg" )
        if TRACE :
            WGTracePrint("Screen capture complete.")

# Helper function to which takes seconds and returns (hours, minutes).
############################################################################
def stot( sec ):
    min = sec.seconds // 60
    hrs = min // 60
    return ( hrs, min % 60 )


# Given a sunrise and sunset time string (sunrise example format '7:00 AM'),
# return true if current local time is between sunrise and sunset. In other
# words, return true if it's daytime and the sun is up. Also, return the 
# number of hours:minutes of daylight in this day. Lastly, return the number
# of seconds until daybreak and sunset. If it's dark, daybreak is set to the 
# number of seconds until sunrise. If it daytime, sunset is set to the number 
# of seconds until the sun sets.
# 
# So, five things are returned as:
#  ( InDaylight, Hours, Minutes, secToSun, secToDark).
############################################################################
def Daylight( sr, st ):
    inDaylight = False  # Default return code.

    # Get current datetime with tz's local day and time.
    tNow = datetime.datetime.now()

    # From a string like '7:00 AM', build a datetime variable for
    # today with the hour and minute set to sunrise.
    t = time.strptime( sr, '%I:%M %p' )     # Temp Var
    tSunrise = tNow                 # Copy time now.
    # Overwrite hour and minute with sunrise hour and minute.
    tSunrise = tSunrise.replace( hour=t.tm_hour, minute=t.tm_min, second=0 )
    
    # From a string like '8:00 PM', build a datetime variable for
    # today with the hour and minute set to sunset.
    t = time.strptime( myDisp.sunset, '%I:%M %p' )
    tSunset = tNow                  # Copy time now.
    # Overwrite hour and minute with sunset hour and minute.
    tSunset = tSunset.replace( hour=t.tm_hour, minute=t.tm_min, second=0 )

    # Test if current time is between sunrise and sunset.
    if (tNow > tSunrise) and (tNow < tSunset):
        inDaylight = True       # We're in Daytime
        tDarkness = tSunset - tNow  # Delta seconds until dark.
        tDaylight = 0           # Seconds until daylight
    else:
        inDaylight = False      # We're in Nighttime
        tDarkness = 0           # Seconds until dark.
        # Delta seconds until daybreak.
        if tNow > tSunset:
            # Must be evening - compute sunrise as time left today
            # plus time from midnight tomorrow.
            tMidnight = tNow.replace( hour=23, minute=59, second=59 )
            tNext = tNow.replace( hour=0, minute=0, second=0 )
            tDaylight = (tMidnight - tNow) + (tSunrise - tNext)
        else:
            # Else, must be early morning hours. Time to sunrise is 
            # just the delta between sunrise and now.
            tDaylight = tSunrise - tNow

    # Compute the delta time (in seconds) between sunrise and set.
    dDaySec = tSunset - tSunrise        # timedelta in seconds
    (dayHrs, dayMin) = stot( dDaySec )  # split into hours and minutes.
    
    return ( inDaylight, dayHrs, dayMin, tDaylight, tDarkness )

#==============================================================
#==============================================================

mode = 'w'      # Default to weather mode.
details_day = 0

# Create an instance of the lcd display class.
myDisp = SmDisplay()

running = True      # Stay running while True
s = 0           # Seconds Placeholder to pace display.
dispTO = 0      # Display timeout to automatically switch back to weather dispaly.

myDisp.restore_data()
# Loads data from Weather.com into class variables.
myDisp.UpdateWeather()
if TRACE :
    WGTracePrint('temp is ' + myDisp.temp)
myDisp.UpdateInsideData()
myDisp.FurnaceFanControl()

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
while running:

    # Look for mouse clicks on tab "buttons"
    click = pygame.mouse.get_pressed()
    if click[0] == 1 : # mouse button pressed
        mouse = pygame.mouse.get_pos()
        # Not straight forward, but I'm taking advantage of the fact that all tabs are the same
        # height and this is much faster than the more stright forward ways.
        if mouse[0] > TAB_BUTTONS[0][0] : # mouse is right of the left-hand-side of the column of buttons
            if mouse[0] < TAB_BUTTONS[0][0] + TAB_BUTTONS[0][2] : #  mouse is left of the right-hand-side of the column of buttons
                # which button is it?
                i = math.trunc(mouse[1] / TAB_BUTTONS[0][3]) # modulo button height
                if i == 0  :
                    mode = 'w' # TAB_WEATHER
                elif i == 1 :
                    mode = 'a' # TAB_ALMANAC
                elif i == 2 :
                    mode = '!' # TAB_ALERT
                elif i == 3 :
                    mode = 'h' # TAB_HISTORY
                elif i == 4 :
                    mode = 'd' # TAB_DETAILS
                if i < 5 :
                    dispTO = 0
   
    # Look for and process keyboard events to change modes.
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            # On 'q' or keypad enter key, quit the program.
            if (( event.key == K_KP_ENTER ) or (event.key == K_q)):
                running = False

            # On '1' key (unshifted !, set mode to 'alert'.
            elif ( event.key == K_1 ):
                mode = '!'
                dispTO = 0

            # On 'w' key, set mode to 'weather'.
            elif ( event.key == K_w ):
                mode = 'w'
                dispTO = 0

            # On 's' key, save a screen shot.
            elif ( event.key == K_s ):
                myDisp.screen_cap()

            # On 'a' key, set mode to 'almanac'.
            elif ( event.key == K_a ):
                mode = 'a'
                dispTO = 0

            # On 'h' key, set mode to 'history'
            elif (event.key == K_h) :
                mode = 'h'
                dispTO = 0

            # On 'd' key, set mode to 'details'
            elif (event.key == K_d) :
                details_day = 0
                mode = 'd'
                dispTO = 0

    # Automatically switch back to weather display after a minute
    if mode != 'w':
        dispTO += 1
        if dispTO > 600:   # One minute timeout at 100ms loop rate.
            mode = 'w'
    else:
        dispTO = 0
        # Look for mouse clicks on the forecast windows to display details
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        if click[0] == 1 : # mouse click in 'weather' mode, might be a forecast button
            # Not straight forward, but I'm relying on all buttons being the same width
            # and it is faster than the straight forward ways.
            if mouse[1] > FORECAST_BUTTONS[0][1] : # below the top of the row of buttons
                if mouse[1] < FORECAST_BUTTONS[0][1] + FORECAST_BUTTONS[0][3] : # above bottom of the row of buttons
                    i = math.trunc(mouse[0] / FORECAST_BUTTONS[0][2]) # modulo button width
                    if i < 4 : 
                        details_day = i
                        mode = 'd'

    # Alert Display Mode
    if ( mode == '!' ):
        # Update / Refresh the display after each second.
        if ( s != time.localtime().tm_sec ):
            s = time.localtime().tm_sec
            myDisp.disp_alert()
        
    # Weather Display Mode
    if (mode == 'w') :
        # Update / Refresh the display after each second.
        if (s != time.localtime().tm_sec) :
            s = time.localtime().tm_sec
            myDisp.disp_weather()   
        # Every ten minutes, update the weather from the net.
        if (time.localtime().tm_min % 10 == 0) and (time.localtime().tm_sec == 0) :
            myDisp.UpdateWeather()
            myDisp.UpdateInsideData()
            myDisp.FurnaceFanControl()
        
    # History display mode
    if (mode == 'h') :
        myDisp.disp_history()
        
    # Details display mode
    if (mode == 'd') :
        myDisp.disp_details(details_day) # today by default


    # Almanac display mode
    if ( mode == 'a'):
        # Pace the screen updates to once per second.
        if s != time.localtime().tm_sec:
            s = time.localtime().tm_sec     

            ( inDaylight, dayHrs, dayMins, tDaylight, tDarkness) = Daylight( myDisp.sunrise, myDisp.sunset )

            # Stat Screen Display.
            myDisp.disp_almanac(inDaylight, dayHrs, dayMins, tDaylight, tDarkness)
        # Refresh the weather data every ten minutes
        if (time.localtime().tm_min % 10 == 0) and (time.localtime().tm_sec == 0) :
            myDisp.UpdateWeather()

    ( inDaylight, dayHrs, dayMins, tDaylight, tDarkness) = Daylight( myDisp.sunrise, myDisp.sunset )

    # Loop timer.
    pygame.time.wait( 100 )


pygame.quit()

