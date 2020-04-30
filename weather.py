# pylint: disable=R0911
# pylint: disable=R0912
# pylint: disable=R0915
# pylint: disable=W0702
# pylint: disable=W0401
# pylint: disable=C0302
# pylint: disable=E0401
# pylint: disable=R0902
# pylint: disable=R0914
# pylint: disable=R0913
# pylint: disable=W0125
# pylint: disable=e0602

#!/usr/bin/python3
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Portions Copyright (c) 2014 Jim Kemp <kemp.jim@gmail.com>
# Majority Copyright (c) 2018-2020 Wayne Geiser <wayne@geiserweb.com>

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
import os
from urllib.request import urlretrieve
import time
import datetime
import math
import textwrap
import pickle
from pygame.locals import *
import pygame

# My local packages
from wg_helper import wg_trace_print
from wg_helper import wg_error_print
from wg_helper import wg_trace_pprint
from wg_helper import wg_init_log
from wg_radio_thermostat import radtherm_set_str
from wg_radio_thermostat import RADTHERM_STR_ERROR
from wg_radio_thermostat import radtherm_status
from wg_radio_thermostat import HOLD_ENABLED
from wg_radio_thermostat import radtherm_get_int
from wg_radio_thermostat import RADTHERM_INT_ERROR
from wg_radio_thermostat import TMODE_HEAT
from wg_radio_thermostat import FAN_ON
from wg_radio_thermostat import radtherm_set_int
from wg_radio_thermostat import SAVE_ENERGY_MODE_ENABLE
from wg_radio_thermostat import radtherm_get_float
from wg_radio_thermostat import SAVE_ENERGY_MODE_DISABLE
from wg_radio_thermostat import RADTHERM_FLOAT_ERROR
from wg_radio_thermostat import radtherm_set_float
from wg_radio_thermostat import FAN_CIRC
from wg_radio_thermostat import radtherm_get_todays_highest_setting
from wg_radio_thermostat import radtherm_get_todays_lowest_setting
from wg_thingspeak import thingspeakgetfloat
from wg_thingspeak import TS_BASEMENT_CHAN
from wg_thingspeak import THINGSPEAK_FLOAT_ERROR
from wg_thingspeak import thingspeaksendfloatnum
from thingspeak_channels_keys import TS_THERM_CHAN
from thingspeak_channels_keys import TS_WEATHER_CHAN
from wg_twilio import sendtext
from dark_sky import getweatherdata
from dark_sky import moonphaseurl

__version__ = "v2.3"
TRACE = False       # write tracing lines to log file
CONTROL_LOG = True  # write lines to show control functions
ALERT = True        # For testing purposes, don't send text alerts
FURNACE_TRACE = False # Trace messages for the furnace control code

# Config for climate control functions
FLOOR_TEMP_DIFFERENTIAL = 5
SAVE_ENERGY_WHEN_FAN_ON = False # When we are running the fan to spread basement heat, turn the tstat down?

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

# Misc constants
COLOR_BLACK = (0, 0, 0)
COLOR_BLUE = (100, 149, 237)
COLOR_RED = (220, 20, 60)
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

TEMP_DEFAULT = -99.0
BARO_DEFAULT = -99.0
HUMID_DEFAULT = -99

# Control tabs
TAB_LABELS = ["Weather", "Almanac", "Alert", "History", "Details"]
TAB_WEATHER = 0
TAB_ALMANAC = 1
TAB_ALERT = 2
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

FFC_STATE = {'beenhere' : False,    # State variable to know when we've
             'fmode' : -1,       # here before and what to return the
             'temp' : -1}        # thermostat values to that we have changed

DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

###############################################################################
#   Raspberry Pi Weather Display
#   By: Jim Kemp    10/25/2014
#   And: Wayne Geiser   2018
###############################################################################
MODE = 'w'      # Default to weather mode.

####################################################################
#
# Should the furnace fan come on?  That is, is the family room temp
# enough higher than the hallway to warrant blowing air around the
# house?
#
def furnacefancontrol():
    """Turn on the furnace fan if we want to move air around"""
    # Get the temperature from the basement sensor
    basement_temp = thingspeakgetfloat(TS_BASEMENT_CHAN, "1", FURNACE_TRACE)
    if basement_temp == THINGSPEAK_FLOAT_ERROR:
        return # try again the next time
    basement_humidity = thingspeakgetfloat(TS_BASEMENT_CHAN, "2", FURNACE_TRACE)
    if basement_humidity == THINGSPEAK_FLOAT_ERROR:
        return # try again the next time
    strret = radtherm_set_str("uma_line0", "Basement T/H: " + str(basement_temp) +
                              "/" + str(basement_humidity) + "%", FURNACE_TRACE)
    if strret == RADTHERM_STR_ERROR:
        wg_error_print("FurnaceFanControl", "Warning, unable to set user line 0 values")
        # Don't have to skip out as this isn't critical

    tstat_status = radtherm_status()
    if 'error' in tstat_status:
        wg_error_print("FurnaceFanControl",
                       "Error getting thermostat status.  Skipping thermostat control")
        return  # try again the next time
    wg_trace_print(str(tstat_status), FURNACE_TRACE)
    tstat_temp = tstat_status['temp']       # air temp
    fan = tstat_status['fmode']     # fan mode
    tmode = tstat_status['tmode']   # thermostat mode (heat?)
    if tstat_status['hold'] == HOLD_ENABLED:
        return # don't mess with the settings, someone wants them this way
    mode_ret = radtherm_get_int("mode", FURNACE_TRACE)
    if mode_ret == RADTHERM_INT_ERROR:
        return  # try again next time
    # Is the thermostat set to "heat" (i.e., it's "winter")?
    if tmode == TMODE_HEAT:
        # If the temperature in the basement is the right number of degrees hotter than the hallway
        if tstat_temp < (basement_temp - FLOOR_TEMP_DIFFERENTIAL):
            # and the fan is not on
            if (fan != FAN_ON) and not FFC_STATE['beenhere']:
                if SAVE_ENERGY_WHEN_FAN_ON:
                    # Set to Save Energy mode temporarily to get the target temp
                    intret = radtherm_set_int("mode", SAVE_ENERGY_MODE_ENABLE, FURNACE_TRACE)
                    if intret == RADTHERM_INT_ERROR:
                        return # try again next time
                    tstat_set = radtherm_get_float("t_heat", FURNACE_TRACE)
                    # Reset Save energy mode (do this regardless of whether the "GetFloat" call
                    # worked or it'll leave the tstat in SAVE ENERGY mode)
                    intret = radtherm_set_int("mode", SAVE_ENERGY_MODE_DISABLE, FURNACE_TRACE)
                    if intret == RADTHERM_INT_ERROR or tstat_set == RADTHERM_FLOAT_ERROR:
                        return # try again next time
                FFC_STATE['fmode'] = fan
                # Turn the furnace fan on
                intret = radtherm_set_int("fmode", FAN_ON, FURNACE_TRACE)
                if intret == RADTHERM_INT_ERROR:
                    return # try again next time
                if SAVE_ENERGY_WHEN_FAN_ON:
                    # Set temp target temperature
                    floatret = radtherm_set_float("t_heat", tstat_set, FURNACE_TRACE)
                    if floatret == RADTHERM_FLOAT_ERROR:
                        # Fix anything we were successful at and leave
                        intret = radtherm_set_int("fmode", FFC_STATE['fmode'], FURNACE_TRACE)
                        return # try again next time
                FFC_STATE['beenhere'] = True    # do this as late as possible
                wg_trace_print("Turned the furnace fan on", CONTROL_LOG)
        else:
            # else, if the furnace fan is on
            if (fan == FAN_ON) and FFC_STATE['beenhere']:
                if SAVE_ENERGY_WHEN_FAN_ON:
                    # Set Save energy mode on and then off again to run the current program
                    intret = radtherm_set_int("mode", SAVE_ENERGY_MODE_ENABLE, FURNACE_TRACE)
                    if intret == RADTHERM_INT_ERROR:
                        return # try again next time
                    intret = radtherm_set_int("mode", SAVE_ENERGY_MODE_DISABLE, FURNACE_TRACE)
                    if intret == RADTHERM_INT_ERROR:
                        return # try again next time
                # Return the thermostat to its former setting
                # Last call to the thermostat as if one of the previous fails,
                # we might be stuck without adjusting 'beenhere'
                intret = radtherm_set_int("fmode", FFC_STATE['fmode'], FURNACE_TRACE)
                if intret == RADTHERM_INT_ERROR:
                    return # try again next time
                FFC_STATE['beenhere'] = False
                wg_trace_print("Returned the furnace fan to previous values", CONTROL_LOG)
    else:
        # we're not in the heating season, figure out if we want the fan on circulate
        # if the temperature in the basement is the right number of degrees cooler than the hallway
        if (tstat_temp - FLOOR_TEMP_DIFFERENTIAL) > basement_temp:
            # and the fan is not set to circulate
            if (fan != FAN_CIRC) and not FFC_STATE['beenhere']:
                FFC_STATE['fmode'] = fan
                # Turn the furnace fan to circulate
                intret = radtherm_set_int("fmode", FAN_CIRC, FURNACE_TRACE)
                if intret == RADTHERM_INT_ERROR:
                    return # try again next time
                wg_trace_print("Turned the furnace fan to circulate", CONTROL_LOG)
                FFC_STATE['beenhere'] = True
        else:
            # else, if the furnace fan is set to circulate
            if (fan == FAN_CIRC) and FFC_STATE['beenhere']:
                # return the furnace fan to its previous setting
                intret = radtherm_set_int("fmode", FFC_STATE['fmode'], FURNACE_TRACE)
                if intret == RADTHERM_INT_ERROR:
                    return # try again next time
                wg_trace_print("Turned the furnace fan to auto", CONTROL_LOG)
                FFC_STATE['beenhere'] = False

####################################################################
#
# If the weather forecast is for warm weather, adjust the thermostat
# setting so as to let the weather heat the house more
#
# If the thermostat is at its highest setting (i.e., not set back)
# and the forecast high temperature for the day is greater than or
# equal to that highest setting, set the thermostat to halfway
# between the highest and lowest setting for the day.
#
def adjusttstatsetting(forecast_high):
    """Adjust the thermostat setting based on the weather forecast"""
    # what is the tstat's current setting?
    tstat_status = radtherm_status()
    if 'error' in tstat_status:
        wg_error_print("adjusttstatsetting",
                       "Error getting thermostat status.  Skipping thermostat control")
        return  # try again the next time
    if tstat_status['hold'] == HOLD_ENABLED:
        return # don't mess with the settings, someone wants them this way
    tmode = tstat_status['tmode']   # thermostat mode (heat?)
    if tmode == TMODE_HEAT:
        tstat_high = radtherm_get_todays_highest_setting(TRACE)
        if tstat_high == RADTHERM_FLOAT_ERROR:
            wg_error_print("adjusttstatsetting", "Error getting highest setting")
            return # Try again next time
        tstat_temp = tstat_status['t_heat']
        wg_trace_print("tstat_high = " + str(tstat_high) + ", tstat_temp = " + str(tstat_temp), TRACE)
        if tstat_temp == tstat_high:
            high_temp = int(forecast_high.split('°')[0])
            wg_trace_print("forecast_high = " + str(forecast_high), TRACE)
            wg_trace_print("high_temp = " + str(high_temp), TRACE)
            if high_temp >= tstat_temp:
                tstat_low = radtherm_get_todays_lowest_setting(TRACE)
                if tstat_low == RADTHERM_FLOAT_ERROR:
                    wg_error_print("adjusttstatsetting", "Error getting lowest setting")
                    return # Try again next time
                setback_temp = tstat_high - (tstat_high - tstat_low) / 2
                wg_trace_print("tstat_low = " + str(tstat_low) + ", setback_temp = " + str(setback_temp), TRACE)
                floatret = radtherm_set_float("t_heat", setback_temp, TRACE)
                if floatret == RADTHERM_FLOAT_ERROR:
                    wg_error_print("adjusttstatsetting", "Error setting t_heat")
                    return
                wg_trace_print(("T-stat is set to " + str(tstat_temp) +
                                ", Forecast high temp is " + str(high_temp) +
                                ", highest tstat setting is " + str(tstat_high) +
                                ", Set the thermostat to " + str(setback_temp)), CONTROL_LOG)


####################################################################
#
# Get data from interior data sources and update ThingSpeak
def updateinsidedata():
    """Get data from the interior data sources and update ThingSpeak"""
    wg_trace_print("Updating inside data", TRACE)
    tmp = radtherm_get_float("temp", TRACE)
    if tmp != RADTHERM_FLOAT_ERROR:
        # Get the humidity from the hall thermostat
        wg_trace_print("Get thermostat humidity data", TRACE)
        humid = radtherm_get_float("humidity", TRACE)
        wg_trace_print("Thermostat returned humid = " + str(humid), TRACE)
        if humid != RADTHERM_FLOAT_ERROR:
            thingspeaksendfloatnum(TS_THERM_CHAN, 2, "1", tmp, "2", humid, " ", 0, " ", 0, TRACE)

###############################################################################
#
# Return proper color for rising and falling values
#
###############################################################################
def color_rising_falling(old, new, curr_color):
    """Return the correct color if a value iw rising or falling"""
    retcolor = curr_color
    if new > old:
        retcolor = COLOR_TEXT_RISING
    elif new < old:
        retcolor = COLOR_TEXT_FALLING
    return retcolor

###############################################################################
#
#   Saves an URL file to a disk file to avoid Internet calls later
#
###############################################################################
def saveurltofile(url, fil_name):
    """Cache an URL to a disk file if we haven't already done so"""
    # create the icons directory if it doesn't exist
    folder = RUNNING_LOC + 'icons'
    if not os.path.exists(folder):
        os.makedirs(folder)
    fil = folder + "/" + fil_name + ".gif"
    wg_trace_print(url, TRACE)
    wg_trace_print(fil, TRACE)
    # Does it already exist?
    if  not os.path.isfile(fil):
        # save the URL to a disk file
        urlretrieve(url, fil)
    # return the fileneme
    return fil

# Small LCD Display.
class SmDisplay:
    """Class for application"""
    screen = None

    ###############################################################################
    #
    # Handle weather alerts
    #
    ###############################################################################
    def handle_alerts(self, weatherdata):
        """Send any alerts that we haven't already sent"""
        try:
            if not weatherdata['alerts']: # No alerts to deal with, clear the saved list
                self.alerts_sent = []
            else:
                for alert in weatherdata['alerts']:
                    # check to see if we've already sent this one
                    send_it = True
                    for already_sent in self.alerts_sent:
                        if already_sent != weatherdata['alerts'].pop:
                            send_it = False
                            break
                    if send_it:
                        alert_msg = 'Alert: %s' % (alert)
                        if ALERT:
                            sendtext(alert_msg)
                        # Update alert list after sending in case there was an error in sending
                        # it.  That way, we'll try to send it again next time.
                        self.alerts_sent.append(alert)
        except:
            wg_error_print("UpdateWeather", "Alert Exception")
            wg_trace_pprint(weatherdata['alerts'], True)

    ###############################################################################
    #
    # Track some data for future research
    #
    ###############################################################################
    def log_research_data(self):
        """Keep track of a few pieces of data for further research"""
        try:
            # if it's the top of the hour
            if time.localtime().tm_min < 10:
                # save date, hour, thermostat temp, forecast data to .csv file
                fil = open("hourly_data.csv", "a+")
                rightnow = datetime.datetime.now()
                tstat_temp = radtherm_get_float("temp", TRACE)
                if tstat_temp != RADTHERM_FLOAT_ERROR:
                    fil.write(str(rightnow.month) + "/" +
                              str(rightnow.day) + "/" +
                              str(rightnow.year) + ", " +
                              str(rightnow.hour) + ":00, " +
                              str(tstat_temp) + ", " +
                              str(self.temps[0][0]) + ", " +
                              str(self.temps[0][1]) + ", " +
                              self.data['rain'][0])
                fil.close()
        except:
            wg_error_print("UpdateWeather", "Tracking data output error.")
            # Don't know what else we can do!

    ###########################################################################
    #
    # Load the font from a file if I can't find it native
    #
    # Note, for efficiency, we save a loaded font under its name and size
    # so we don't have to reload it.
    #
    ###########################################################################
    def loadfont(self, font_name, size):
        """Load non-native fonts from a file"""
        # Have we already loaded (and saved) the font of this name & size?
        for font in self.fonts:
            if (font[0] == font_name) and (font[1] == size):
                return font[2]
        # I guess not, load it up
        if self.load_fonts_from_file:
            txt = font_name + "Bold.ttf"
            osfont = pygame.font.Font(os.path.join(FONT_LOC_ON_RASPBERRY_PI, txt), size)
        else:
            osfont = pygame.font.SysFont(font_name, size, bold=1)
        # save it in the list for future calls
        self.fonts.append([font_name, size, osfont])
        return osfont


    ####################################################################
    def __init__(self):
        # "Initializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        disp_no = os.getenv("DISPLAY")
        wg_trace_print("X Display = " + str(disp_no), (disp_no and TRACE))

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
                wg_trace_print("Driver: " + str(driver) + " failed.", TRACE)
                continue
            found = True
            break

        if not found:
            raise Exception('No suitable video driver found!')

        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        wg_trace_print("Framebuffer Size: " + str(size[0]) + " x " + str(size[1]), TRACE)
        if RUNNING_ON == RASPBERRY_PI:
            self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
        else:
            # Make a window rather than using the entire display
            if DISPLAY_SIZE == DISPLAY_SMALL:
                size = (DISPLAY_SMALL_WIDTH, DISPLAY_SMALL_HEIGHT)
            elif DISPLAY_SIZE == DISPLAY_WIDE:
                size = (DISPLAY_WIDE_WIDTH, DISPLAY_WIDE_HEIGHT)
            else:
                size = (DISPLAY_LARGE_WIDTH, DISPLAY_LARGE_HEIGHT)
            self.screen = pygame.display.set_mode(size)
            pygame.display.flip()
        # Clear the screen to start
        self.screen.fill(COLOR_BACKGROUND)
        # Initialise font support
        pygame.font.init()
        # Render the screen
        pygame.display.update()
        self.data = dict()
        self.data['curr_cond'] = ""
        self.data['temp'] = str(TEMP_DEFAULT)
        self.data['tempcolor'] = COLOR_TEXT_NORMAL
        self.data['windchill'] = 0
        self.data['wind_speed'] = 0
        self.data['vis'] = 0
        self.data['baro'] = BARO_DEFAULT
        self.data['barocolor'] = COLOR_TEXT_NORMAL
        self.data['wind_dir'] = 'S'
        self.data['gust'] = "N/A"
        self.data['humid'] = HUMID_DEFAULT
        self.data['humidcolor'] = COLOR_TEXT_NORMAL
        self.data['update'] = ''
        self.data['day'] = ['', '', '', '']
        self.data['icon'] = [0, 0, 0, 0]
        self.data['rain'] = ['', '', '', '']
        self.forecastdetails = [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ']
        self.temps = [['', ''], ['', ''], ['', ''], ['', '']]
        self.sunrise = '7:00 AM'
        self.sunset = '8:00 PM'
        self.data['moonrise'] = 'N/A'
        self.data['moonset'] = 'N/A'
        self.data['moonicon'] = ""
        # Remember min and max temperatures
        self.max_temps = [0, 0, 0, 0, 0, 0, 0]
        self.min_temps = [0, 0, 0, 0, 0, 0, 0]
        # self.rainfall = [0, 0, 0, 0, 0, 0, 0]
        self.curr_day = int(time.strftime("%w"))
        # Remember if we are loading fonts from a file
        fonts = pygame.font.get_fonts()
        if str(fonts[0]) == "None":
            self.load_fonts_from_file = True
        else:
            self.load_fonts_from_file = False
        self.fonts = []
        self.alerts_sent = []

        if DISPLAY_SIZE == DISPLAY_SMALL:
            self.xmax = DISPLAY_SMALL_WIDTH - 35
            self.ymax = DISPLAY_SMALL_HEIGHT - 5
            self.data['scaleicon'] = True       # Weather icons need scaling.
            self.data['subwinth'] = 0.05        # Sub window text height
            self.data['tmdateth'] = 0.100       # Time & Date Text Height
            self.data['tmdatesmth'] = TEXT_HEIGHT_SMALL
            self.data['tmdateypos'] = 10        # Time & Date Y Position
            self.data['tmdateypossm'] = 18      # Time & Date Y Position Small
        elif DISPLAY_SIZE == DISPLAY_WIDE:
            self.xmax = DISPLAY_SMALL_WIDTH - 35 # extra room on the side for buttons
            self.ymax = DISPLAY_WIDE_HEIGHT - 5
            self.data['scaleicon'] = False      # No icon scaling needed.
            self.data['subwinth'] = 0.04        # Sub window text height
            self.data['tmdateth'] = 0.11       # Time & Date Text Height
            self.data['tmdatesmth'] = 0.06
            self.data['tmdateypos'] = 1         # Time & Date Y Position
            self.data['tmdateypossm'] = 8       # Time & Date Y Position Small
        else: # DISPLAY_LARGE
            self.xmax = DISPLAY_LARGE_WIDTH - 35
            self.ymax = DISPLAY_LARGE_HEIGHT - 5
            self.data['scaleicon'] = False      # No icon scaling needed.
            self.data['subwinth'] = 0.065       # Sub window text height
            self.data['tmdateth'] = 0.125       # Time & Date Text Height
            self.data['tmdatesmth'] = 0.075
            self.data['tmdateypos'] = 1         # Time & Date Y Position
            self.data['tmdateypossm'] = 8       # Time & Date Y Position Small


    ####################################################################
    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    ###########################################################################
    #
    # Draw the tab rectangles on the left hand side of the screen.
    # arguments -
    #   which - which tab is currently being displayed (see the top of the
    #           file for enumerated list of tabs)
    #
    ###########################################################################
    def draw_tabs(self, which):
        """Draw the right hand tabs / buttons"""
        button_height = (self.ymax*0.15)-2 # 15% of screen height
        p_top = 2
        p_bottom = p_top + button_height
        p_left = self.xmax
        p_right = DISPLAY_WIDTH-3
        # If we have alerts, draw the outline in red
        if not self.alerts_sent:
            color = COLOR_WHITE
        else:
            color = COLOR_RED
        # draw the top line
        if which == 0:
            pygame.draw.line(self.screen, color, (p_left+3, p_top), (p_right+2, p_top),
                             BORDER_WIDTH)
        else:
            pygame.draw.line(self.screen, COLOR_GREY, (p_left+3, p_top), (p_right+2, p_top),
                             BORDER_WIDTH)
        # draw the left, right, and bottom of each of the buttons
        for i in range(TAB_LAST + 1):
            # remember the tab rectangle that we can use as a button
            TAB_BUTTONS[i][0] = p_left
            TAB_BUTTONS[i][1] = p_top
            TAB_BUTTONS[i][2] = (p_right-p_left)
            TAB_BUTTONS[i][3] = button_height
            if which == i: # active tab
                txtclr = COLOR_TEXT_NORMAL
                lftclr = COLOR_BACKGROUND
                rgtclr = color
            else:
                txtclr = COLOR_GREY
                lftclr = color
                rgtclr = COLOR_GREY
            pygame.draw.line(self.screen, lftclr, (p_left, p_top+3),
                             (p_left, p_bottom-3), BORDER_WIDTH) # left
            pygame.draw.line(self.screen, rgtclr, (p_right, p_top+3),
                             (p_right, p_bottom), BORDER_WIDTH) # right
            if which == i:     # redraw the top as it should have been white
                pygame.draw.line(self.screen, color, (p_left+3, p_top),
                                 (p_right+2, p_top), BORDER_WIDTH)
            pygame.draw.line(self.screen, rgtclr, (p_left+3, p_bottom),
                             (p_right+2, p_bottom), BORDER_WIDTH) # bottom
            p_top = p_top + button_height
            p_bottom = p_bottom + button_height
            font = self.loadfont(FONT_NORMAL, int(self.ymax*TEXT_HEIGHT_SMALL))
            txt = font.render(TAB_LABELS[i], True, txtclr)
            (_, txt_hei) = txt.get_size()
            self.screen.blit(txt, (self.xmax+BORDER_WIDTH,
                                   self.ymax*(0.15*(i+1))-BORDER_WIDTH-txt_hei))

    ###########################################################################
    #
    # Draw the outline
    #
    ###########################################################################
    def draw_screen_outline(self):
        """Draw the border lines"""
        # If we have alerts, draw the outline in red
        if not self.alerts_sent:
            color = COLOR_WHITE
        else:
            color = COLOR_RED
        # Draw Screen Border
        pygame.draw.line(self.screen, color, (0, 2), (self.xmax+2, 2),
                         BORDER_WIDTH) # top border
        pygame.draw.line(self.screen, color, (2, 2), (2, self.ymax),
                         BORDER_WIDTH) # left border
        pygame.draw.line(self.screen, color, (0, self.ymax+2),
                         (self.xmax+2, self.ymax+2), BORDER_WIDTH) # Bottom border
        pygame.draw.line(self.screen, color, (self.xmax, 2),
                         (self.xmax, self.ymax), BORDER_WIDTH) # right border
        # Add Weather Underground logo to bottom right hand corner of the screen
        icon = pygame.image.load(os.path.join(RUNNING_LOC, "dark-sky-logo.gif"))
        (logo_wid, logo_hei) = icon.get_size()
        self.screen.blit(icon, (self.xmax+BORDER_WIDTH, self.ymax-logo_hei+BORDER_WIDTH))
        # Display version string
        font = self.loadfont(FONT_NORMAL, int(self.ymax*TEXT_HEIGHT_SMALL))
        txt = font.render(__version__, True, COLOR_TEXT_NORMAL)
        (_, vstr_wid) = txt.get_size()
        self.screen.blit(txt, (self.xmax+logo_wid+BORDER_WIDTH+2, self.ymax-vstr_wid))

    ###########################################################################
    #
    # Save interesting stuff to disk
    #
    ###########################################################################
    def save_data(self):
        """save data to disk"""
        pickle.dump(self.max_temps, open("max_temps.p", "wb"))
        pickle.dump(self.min_temps, open("min_temps.p", "wb"))
        # pickle.dump(self.rainfall, open("rainfall.p", "wb"))

    ###########################################################################
    #
    # Restore interesting stuff from disk
    #
    ###########################################################################
    def restore_data(self):
        """restore saved data from disk"""
        self.max_temps = pickle.load(open("max_temps.p", "rb"))
        self.min_temps = pickle.load(open("min_temps.p", "rb"))
        # self.rainfall = pickle.load(open("rainfall.p", "rb"))

    ###########################################################################
    #
    # Draw the time and date at the top of the screen
    #
    ###########################################################################
    def draw_time_and_date(self):
        """Draw the time and date"""
        # If we have alerts, draw the outline in red
        if not self.alerts_sent:
            color = COLOR_WHITE
        else:
            color = COLOR_RED
        pygame.draw.line(self.screen, color, (2, self.ymax*0.15),
                         (self.xmax, self.ymax*0.15), BORDER_WIDTH)

        # Time & Date
        font = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['tmdateth']))
        sfont = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['tmdatesmth']))

        rtm1 = font.render(time.strftime("%a, %b %d   %I:%M", time.localtime()),
                           True, COLOR_TEXT_NORMAL)
        (tx1, _) = rtm1.get_size()
        rtm2 = sfont.render(time.strftime("%S", time.localtime()),
                            True, COLOR_TEXT_NORMAL)
        (tx2, _) = rtm2.get_size()
        rtm3 = font.render(time.strftime(" %p", time.localtime()),
                           True, COLOR_TEXT_NORMAL)
        (tx3, _) = rtm3.get_size()

        tpos = self.xmax / 2 - (tx1 + tx2 + tx3) / 2
        self.screen.blit(rtm1, (tpos, self.data['tmdateypos']))
        self.screen.blit(rtm2, (tpos+tx1+3, self.data['tmdateypossm']))
        self.screen.blit(rtm3, (tpos+tx1+tx2, self.data['tmdateypos']))

        if self.curr_day != int(time.strftime("%w")): # it's a new day!
            self.curr_day = int(time.strftime("%w"))
            self.max_temps[self.curr_day] = 0
            self.min_temps[self.curr_day] = 0
            # self.rainfall[self.curr_day] = 0
            self.save_data()

    ####################################################################
    #
    # Get data from local station via weather source
    def updateweather(self):
        """Get data from the weather source"""
        wg_trace_print("in updateweather", TRACE)
        if self.data['temp'] == '??':
            oldtemp = TEMP_DEFAULT # keep it from crashing
        else:
            oldtemp = float(self.data['temp'])
        oldbaro = float(self.data['baro'])
        oldhumid = float(self.data['humid'])

        weatherdata = dict()
        if not getweatherdata(weatherdata):
            self.data['temp'] = '??'
            self.data['update'] = ''
            wg_error_print("updateweather", "Unable to get Weather Data")
            return

        self.handle_alerts(weatherdata) # send out any new alerts

        try:
            self.data['update'] = weatherdata['observation_time']
            wg_trace_print("New Weather " + self.data['update'], TRACE)
            self.data['temp'] = "%d" % (weatherdata['temp_f'])
            # self.rainfall[self.curr_day] = weatherdata['precip_today_in']
            wg_trace_print('temp is ' + self.data['temp'], TRACE)
            if (self.max_temps[self.curr_day] == 0) and (self.min_temps[self.curr_day] == 0):
                self.min_temps[self.curr_day] = float(self.data['temp'])
                self.max_temps[self.curr_day] = float(self.data['temp'])
                self.save_data()
            # if the value changed from last time, what color should we now display?
            if oldtemp == float(TEMP_DEFAULT):
                self.data['tempcolor'] = COLOR_TEXT_NORMAL
            else:
                self.data['tempcolor'] = color_rising_falling(oldtemp, float(self.data['temp']),
                                                              self.data['tempcolor'])
            if ((float(self.data['temp']) > oldtemp) and
                    (float(self.data['temp']) > self.max_temps[self.curr_day])):
                self.max_temps[self.curr_day] = float(self.data['temp']) # save the new max
                self.save_data()
            elif ((float(self.data['temp']) < oldtemp) and
                  (float(self.data['temp']) < self.min_temps[self.curr_day])):
                self.min_temps[self.curr_day] = float(self.data['temp']) # save the new min
                self.save_data()
            self.data['curr_cond'] = weatherdata['weather']
            self.data['windchill'] = "%d" % (int(round(float(weatherdata['windchill']))))
            self.data['wind_speed'] = "%d" % (int(weatherdata['wind_mph']))
            self.data['baro'] = weatherdata['pressure_in']
            # if the value changed from last time, what color should we now display?
            if oldbaro == BARO_DEFAULT:
                self.data['barocolor'] = COLOR_TEXT_NORMAL
            else:
                self.data['barocolor'] = color_rising_falling(oldbaro, float(self.data['baro']),
                                                              self.data['barocolor'])
            self.data['wind_dir'] = weatherdata['wind_dir']
            self.data['humid'] = weatherdata['relative_humidity'].rstrip('%')
            wg_trace_print("Sending WU Data to ThingSpeak", TRACE)
            # Tell ThingSpeak what the temperature, humidity, & barometric pressure is
            thingspeaksendfloatnum(TS_WEATHER_CHAN, 3, "1",
                                   self.data['temp'], "2",
                                   self.data['baro'], "3",
                                   self.data['humid'], "", 0, TRACE)
            # if the value changed from last time, what color should we now display?
            if oldhumid == HUMID_DEFAULT:
                self.data['humidcolor'] = COLOR_TEXT_NORMAL
            else:
                self.data['humidcolor'] = color_rising_falling(oldhumid, float(self.data['humid']),
                                                               self.data['humidcolor'])
            self.data['vis'] = weatherdata['visibility_mi']
            self.data['gust'] = '%s' % (int(round(float(weatherdata['wind_gust_mph']))))
            wg_trace_print("forecast data", TRACE)
            wg_trace_pprint(weatherdata['fc'], TRACE)
            wg_trace_pprint(weatherdata['fctxt'], TRACE)
            i = 0
            for day in weatherdata['fc']:
                self.data['day'][i] = day['name']
                self.temps[i][0] = day['high_f']
                self.temps[i][1] = day['low_f']
                self.data['rain'][i] = day['icon']
                self.data['icon'][i] = "./icons/" + day['icon_url']
                i = i + 1
                if i > 3:
                    break
            # There are two forecast details per day (day and night)
            i = 0
            for day in weatherdata['fctxt']:
                self.forecastdetails[i] = day['fcttext']
                i = i + 1
                if i > 3:
                    break
            wg_trace_print("Sun and moon data", TRACE)
            self.sunrise = weatherdata['sunrise']
            self.sunset = weatherdata['sunset']
            self.data['moonrise'] = weatherdata['moonrise']
            self.data['moonset'] = weatherdata['moonset']
            # There are only icons for days 0-27
            if weatherdata['ageOfMoon'] > 27:
                weatherdata['ageOfMoon'] = 0
            ostr = 'moon'+str(weatherdata['ageOfMoon'])
            self.data['moonicon'] = saveurltofile(moonphaseurl() + ostr + '.gif', ostr)
            wg_trace_print('temp is ' + self.data['temp'], TRACE)
        except:
            wg_error_print("updateweather", "Weather Collection Error #2")
            wg_trace_pprint(weatherdata, True)
            self.data['temp'] = '??'
            self.data['update'] = ''

        self.log_research_data()

    ####################################################################
    def disp_weather(self):
        """OUtput weather screen display"""
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)
        xmin = 2
        xmax = self.xmax
        ymax = self.ymax
        # If we have alerts, draw the outline in red
        if not self.alerts_sent:
            color = COLOR_WHITE
        else:
            color = COLOR_RED
        lnclr = COLOR_TEXT_NORMAL
        fnt = FONT_NORMAL

        tempchar = "F"
        barpressstr = "\"Hg"
        speedstr = "mph"
        if self.data['temp'] != "??":
            if (int(self.data['temp']) > 99) or (int(self.data['temp']) < -9):   # three digits
                tempchar = ""              # get rid of the character for F or C

        MYDISP.draw_screen_outline()
        # .15 is 15% down from the top of the screen for date/time underline
        pygame.draw.line(self.screen, color, (xmin, ymax*0.5), (xmax, ymax*0.5), BORDER_WIDTH)
        pygame.draw.line(self.screen, color, (xmax*0.25, ymax*0.5), (xmax*0.25, ymax), BORDER_WIDTH)
        pygame.draw.line(self.screen, color, (xmax*0.5, ymax*0.15), (xmax*0.5, ymax), BORDER_WIDTH)
        pygame.draw.line(self.screen, color, (xmax*0.75, ymax*0.5), (xmax*0.75, ymax), BORDER_WIDTH)

        # remember rectangles for button presses
        FORECAST_BUTTONS[0][0] = xmin       # left
        FORECAST_BUTTONS[1][0] = xmax*0.25
        FORECAST_BUTTONS[2][0] = xmax*0.5
        FORECAST_BUTTONS[3][0] = xmax*0.75
        # all the same top, width, and height
        for i in range(4):
            FORECAST_BUTTONS[i][1] = ymax*0.5                       # top
            FORECAST_BUTTONS[i][2] = (xmax-xmin)*0.25               # width
            FORECAST_BUTTONS[i][3] = ymax - FORECAST_BUTTONS[i][1]  # height

        # Time and date at the top of the scrren
        MYDISP.draw_time_and_date()
        # Draw tabs
        MYDISP.draw_tabs(TAB_WEATHER)

        # Outside Temp
        font = self.loadfont(fnt, int(ymax*(0.5-0.15)*0.9))
        wg_trace_print('temp is ' + self.data['temp'], TRACE)
        txt = font.render(self.data['temp'], True, self.data['tempcolor'])
        (twid, _) = txt.get_size()
        dfont = self.loadfont(fnt, int(ymax*(0.5-0.15)*0.5))
        dtxt = dfont.render("°" + tempchar, True, lnclr)
        (tx2, _) = dtxt.get_size()
        magic = xmax*0.27 - (twid*1.02 + tx2) / 2
        self.screen.blit(txt, (magic, ymax*0.15))
        magic = magic + (twid*1.02)
        self.screen.blit(dtxt, (magic, ymax*0.2))

        # Conditions
        yst = 0.16    # Yaxis Start Pos
        gap = 0.065   # Line Spacing Gap
        txthei = TEXT_HEIGHT_SMALL    # Text Height
        dshei = 0.05    # Degree Symbol Height
        dsyo = 0.01    # Degree Symbol Yaxis Offset
        xsp = 0.52    # Xaxis Start Pos
        x2col = 0.78    # Second Column Xaxis Start Pos

        font = self.loadfont(fnt, int(ymax*txthei))
        txt = font.render('Feels Like', True, lnclr)
        self.screen.blit(txt, (xmax*xsp, ymax*yst))
        txt = font.render(self.data['windchill'], True, lnclr)
        self.screen.blit(txt, (xmax*x2col, ymax*yst))
        (twid, _) = txt.get_size()
        dfont = self.loadfont(fnt, int(ymax*dshei))
        dtxt = dfont.render("°" + tempchar, True, lnclr)
        self.screen.blit(dtxt, (xmax*x2col+twid*1.01, ymax*(yst+dsyo)))

        txt = font.render('Windspeed:', True, lnclr)
        self.screen.blit(txt, (xmax*xsp, ymax*(yst+gap*1)))
        if self.data['wind_speed'] == "calm":
            txt = font.render(self.data['wind_speed'], True, lnclr)
        else:
            txt = font.render(self.data['wind_speed'] + " " + speedstr, True, lnclr)
        self.screen.blit(txt, (xmax*x2col, ymax*(yst+gap*1)))

        txt = font.render('Direction:', True, lnclr)
        self.screen.blit(txt, (xmax*xsp, ymax*(yst+gap*2)))
        txt = font.render(self.data['wind_dir'].upper(), True, lnclr)
        self.screen.blit(txt, (xmax*x2col, ymax*(yst+gap*2)))

        txt = font.render('Barometer:', True, lnclr)
        self.screen.blit(txt, (xmax*xsp, ymax*(yst+gap*3)))
        txt = font.render(self.data['baro'], True, self.data['barocolor'])
        self.screen.blit(txt, (xmax*x2col, ymax*(yst+gap*3)))
        (tx2, _) = txt.get_size()
        txt = font.render(" " + barpressstr, True, lnclr)
        self.screen.blit(txt, (xmax*x2col+tx2, ymax*(yst+gap*3)))

        txt = font.render('Humidity:', True, lnclr)
        self.screen.blit(txt, (xmax*xsp, ymax*(yst+gap*4)))
        txt = font.render(self.data['humid'], True, self.data['humidcolor'])
        self.screen.blit(txt, (xmax*x2col, ymax*(yst+gap*4)))
        (tx2, _) = txt.get_size()
        txt = font.render('%', True, lnclr)
        self.screen.blit(txt, (xmax*x2col+tx2, ymax*(yst+gap*4)))

        swcent = 0.125           # Sub Window Centers
        swy = 0.510           # Sub Windows Yaxis Start
        txthei = self.data['subwinth']       # Text Height
        gap = 0.065           # Line Spacing Gap
        rpl = 5.95            # Rain percent line offset.

        font = self.loadfont(fnt, int(ymax*txthei))

        dyi = -1
        for _ in self.data['day']:
            # Daily forecast sub-windows
            dyi = dyi + 1
            if dyi == 0:
                dytxt = "Today"
            else:
                dytxt = self.data['day'][dyi]
            txt = font.render(dytxt + ':', True, lnclr)
            (twid, _) = txt.get_size()
            self.screen.blit(txt, (xmax*swcent*((dyi*2)+1)-twid/2, ymax*(swy+gap*0)))
            txt = font.render(self.temps[dyi][0] + ' / ' + self.temps[dyi][1], True, lnclr)
            (twid, _) = txt.get_size()
            self.screen.blit(txt, (xmax*swcent*((dyi*2)+1)-twid/2, ymax*(swy+gap*5)))
            txt = font.render(self.data['rain'][dyi], True, lnclr)
            (twid, _) = txt.get_size()
            self.screen.blit(txt, (xmax*swcent*((dyi*2)+1)-twid/2, ymax*(swy+gap*rpl)))
            try:
                # icons have been saved to disk when we got the weather forecast/q/
                # so as to avoid continually going out on the Internet
                icon = pygame.image.load(os.path.join(RUNNING_LOC, self.data['icon'][dyi]))
                (iwid, ihei) = icon.get_size()
                if self.data['scaleicon']:
                    icon2 = pygame.transform.scale(icon, (int(iwid*1.5), int(ihei*1.5)))
                    (iwid, ihei) = icon2.get_size()
                    icon = icon2
                if ihei < 90:
                    yout = (90 - ihei) / 2
                else:
                    yout = 0
                self.screen.blit(icon, (xmax*swcent*((dyi*2)+1)-iwid/2, ymax*(swy+gap*1.2)+yout))
            except:
                # nothing.  We hope it works next time
                wg_error_print("disp_weather",
                               "Icon error: " + dytxt + " " + self.data['icon'][dyi])

        # Update the display
        pygame.display.update()

    ####################################################################
    def disp_alert(self):
        """Display the alert screen"""
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)

        max_lines = 14 # Maximum number of lines from the alert message that will fit on screen

        MYDISP.draw_screen_outline()

        # Time and date at the top of the screen
        MYDISP.draw_time_and_date()
        # Draw tabs
        MYDISP.draw_tabs(TAB_ALERT)

        sfont = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['subwinth']))
        printline = 4

        # No alert, say so
        if not self.alerts_sent:
            printline = printline + 1
            txt = sfont.render("No alert!", True, COLOR_TEXT_NORMAL)
            self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        else:
            # Just do the last alert
            i = 0
            for line in textwrap.wrap(self.alerts_sent[len(self.alerts_sent) - 1], 50,
                                      subsequent_indent="  "):
                printline = printline + 1
                txt = sfont.render(line, True, COLOR_TEXT_NORMAL)
                self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
                i = i + 1
                if i == max_lines:
                    break

        # Update the display
        pygame.display.update()

    ####################################################################
    def sprint(self, ostr, font, xpix, lnum, clr):
        """Print ostr in the requested font and color starting at the requested spot"""
        fstr = font.render(ostr, True, clr)
        self.screen.blit(fstr, (xpix, self.ymax*0.075*lnum))

    ####################################################################
    def disp_almanac(self, isindaylight, dayhrs, daymins, tdaylight, tdarkness):
        """Display the almanac screen"""
        # Fill the screen with black
        self.screen.fill(COLOR_BACKGROUND)
        xmax = self.xmax
        ymax = self.ymax
        lcol = COLOR_TEXT_NORMAL

        tempchar = "F"
        tempvisstr = " mi"
        barpressstr = " \"Hg"
        speedstr = " mph"

        MYDISP.draw_screen_outline()

        # Time and date at the top of the screen
        MYDISP.draw_time_and_date()
        # Draw tabs
        MYDISP.draw_tabs(TAB_ALMANAC)

        sfont = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['tmdatesmth']))
        printline = 3
        ostr = "Sun Rise/Set %s / %s" % (self.sunrise, self.sunset)
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        ostr = "Daylight (Hrs:Min): %d:%02d" % (dayhrs, daymins)
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        if isindaylight:
            ostr = "Sunset in (Hrs:Min): %d:%02d" % stot(tdarkness)
        else:
            ostr = "Sunrise in (Hrs:Min): %d:%02d" % stot(tdaylight)
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        ostr = self.data['update']
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        ostr = "Current Cond: %s" % self.data['curr_cond']
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        ostr = (self.data['temp'] + "°" + tempchar + " " +
                self.data['baro'] + barpressstr +
                " Wnd " +
                self.data['wind_dir'] + " @ " + self.data['wind_speed'])
        if self.data['gust'] != 'N/A':
            ostr = ostr + ' (g ' + str(self.data['gust']) + ') '
        ostr = ostr + speedstr
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        if self.data['vis'] == 0:
            ostr = "Visibility NA"
        else:
            ostr = ("Visability %s" % self.data['vis'] +
                    tempvisstr)
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        printline = printline + 1
        ostr = "Moon Rise/Set %s / %s" % (self.data['moonrise'], self.data['moonset'])
        self.sprint(ostr, sfont, xmax*0.05, printline, lcol)

        # Moon phase
        icon = pygame.image.load(os.path.join(RUNNING_LOC, self.data['moonicon']))
        (iwid, ihei) = icon.get_size()
        self.screen.blit(icon, (xmax-iwid-2, ymax-ihei))

        # Update the display
        pygame.display.update()

    ####################################################################
    #
    # Min and Max temperatures for the past week (or since startup)
    def disp_history(self):
        """Display the history screen (weekly data)"""
        self.screen.fill(COLOR_BACKGROUND)
        MYDISP.draw_screen_outline()
        # Time and date at the top of the scrren
        MYDISP.draw_time_and_date()
        # Draw tabs
        MYDISP.draw_tabs(TAB_HISTORY)

        # Display daily min and max temps
        tempchar = "F"
        #rainunits = "in"
        sfont = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['tmdatesmth']))
        i = self.curr_day
        for j in range(7):
            if ((self.min_temps[i] != 0) or (self.max_temps[i] != 0)):
                #s = "%s - Min: %d°%s, Max: %d°%s, Rain: %s %s" % (DAY_NAMES[i], self.min_temps[i],
                #                                            tempchar, self.max_temps[i], tempchar,
                #                                                    self.rainfall[i], rainunits)
                ostr = "%s - Min: %d°%s, Max: %d°%s" % (DAY_NAMES[i], self.min_temps[i],
                                                        tempchar, self.max_temps[i], tempchar)
                self.sprint(ostr, sfont, self.xmax*0.05, 3+j, COLOR_TEXT_NORMAL)
            i = i - 1
            if i == -1:
                i = 6

        # Update the display
        pygame.display.update()

    ####################################################################
    #
    # Detailed forecast
    #
    # Parameters:
    #   period = what day (0 = today)
    def disp_details(self, period):
        """Display the details screen (forecast data)"""
        self.screen.fill(COLOR_BACKGROUND)
        MYDISP.draw_screen_outline()
        # Time and date at the top of the scrren
        MYDISP.draw_time_and_date()
        # Draw tabs
        MYDISP.draw_tabs(TAB_DETAILS)

        printline = 4
        sfont = self.loadfont(FONT_NORMAL, int(self.ymax*self.data['subwinth']))
        txt = sfont.render(self.data['day'][period], True, COLOR_TEXT_NORMAL)
        self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))
        for oline in textwrap.wrap(self.forecastdetails[period], 50, subsequent_indent="  "):
            printline = printline + 1
            txt = sfont.render(oline, True, COLOR_TEXT_NORMAL)
            self.screen.blit(txt, (self.xmax*0.05, self.ymax*0.05*printline))

        # Update the display
        pygame.display.update()

    # Save a jpg image of the screen.
    ####################################################################
    def screen_cap(self):
        """sAVE A SCREENSHOT"""
        pygame.image.save(self.screen, "screenshot.jpeg")
        wg_trace_print("Screen capture complete.", TRACE)

# Helper function to which takes seconds and returns (hours, minutes).
############################################################################
def stot(sec):
    """Transform seconds to hours and minutes"""
    minutes = sec.seconds // 60
    hrs = minutes // 60
    return (hrs, minutes % 60)


# Given a sunrise and sunset time string (sunrise example format '7:00 AM'),
# return true if current local time is between sunrise and sunset. In other
# words, return true if it's daytime and the sun is up. Also, return the
# number of hours:minutes of daylight in this day. Lastly, return the number
# of seconds until daybreak and sunset. If it's dark, daybreak is set to the
# number of seconds until sunrise. If it daytime, sunset is set to the number
# of seconds until the sun sets.
#
# So, five things are returned as:
#  ( indaylight, Hours, Minutes, secToSun, secToDark).
############################################################################
def daylight(buff):
    """Calculated daylight time"""
    isindaylight = False  # Default return code.

    # Get current datetime with tz's local day and time.
    tnow = datetime.datetime.now()

    # From a string like '7:00 AM', build a datetime variable for
    # today with the hour and minute set to sunrise.
    ttime = time.strptime(buff, '%I:%M %p')     # Temp Var
    tsunrise = tnow                 # Copy time now.
    # Overwrite hour and minute with sunrise hour and minute.
    tsunrise = tsunrise.replace(hour=ttime.tm_hour, minute=ttime.tm_min, second=0)

    # From a string like '8:00 PM', build a datetime variable for
    # today with the hour and minute set to sunset.
    ttime = time.strptime(MYDISP.sunset, '%I:%M %p')
    tsunset = tnow                  # Copy time now.
    # Overwrite hour and minute with sunset hour and minute.
    tsunset = tsunset.replace(hour=ttime.tm_hour, minute=ttime.tm_min, second=0)

    # Test if current time is between sunrise and sunset.
    if tsunrise < tnow < tsunset:
        isindaylight = True       # We're in Daytime
        tdarkness = tsunset - tnow  # Delta seconds until dark.
        tdaylight = 0           # Seconds until daylight
    else:
        isindaylight = False      # We're in Nighttime
        tdarkness = 0           # Seconds until dark.
        # Delta seconds until daybreak.
        if tnow > tsunset:
            # Must be evening - compute sunrise as time left today
            # plus time from midnight tomorrow.
            tmidnight = tnow.replace(hour=23, minute=59, second=59)
            tnext = tnow.replace(hour=0, minute=0, second=0)
            tdaylight = (tmidnight - tnow) + (tsunrise - tnext)
        else:
            # Else, must be early morning hours. Time to sunrise is
            # just the delta between sunrise and now.
            tdaylight = tsunrise - tnow

    # Compute the delta time (in seconds) between sunrise and set.
    ddaysec = tsunset - tsunrise        # timedelta in seconds
    (dayhrs, daymin) = stot(ddaysec)  # split into hours and minutes.

    return (isindaylight, dayhrs, daymin, tdaylight, tdarkness)

#==============================================================
#==============================================================

# Create the .pid file for monit to monitor this process
pid = str(os.getpid())
pidfile = "/tmp/weather.pid"
open(pidfile, 'w').write(pid)

wg_init_log("err.txt")
wg_trace_print("weather station started.  Version: " + __version__, True)
MODE = 'w'      # Default to weather mode.
DETAILS_DAY = 0

# Create an instance of the lcd display class.
MYDISP = SmDisplay()

RUNNING = True      # Stay running while True
SECS = 0           # Seconds Placeholder to pace display.
DISPTO = 0      # Display timeout to automatically switch back to weather display.

MYDISP.restore_data()
# Loads data from Weather.com into class variables.
MYDISP.updateweather()
wg_trace_print('temp is ' + MYDISP.data['temp'], TRACE)
updateinsidedata()
furnacefancontrol()

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
while RUNNING:

    # Look for mouse clicks on tab "buttons"
    CLICK = pygame.mouse.get_pressed()
    if CLICK[0] == 1: # mouse button pressed
        MOUSE = pygame.mouse.get_pos()
        # Not straight forward, but I'm taking advantage of the fact that all tabs are the same
        # height and this is much faster than the more stright forward ways.
        if MOUSE[0] > TAB_BUTTONS[0][0]:
            # mouse is right of the left-hand-side of the column of buttons
            if MOUSE[0] < TAB_BUTTONS[0][0] + TAB_BUTTONS[0][2]:
                #  mouse is left of the right-hand-side of the column of buttons
                # which button is it?
                TABNO = math.trunc(MOUSE[1] / TAB_BUTTONS[0][3]) # modulo button height
                if TABNO == 0:
                    MODE = 'w' # TAB_WEATHER
                elif TABNO == 1:
                    MODE = 'a' # TAB_ALMANAC
                elif TABNO == 2:
                    MODE = '!' # TAB_ALERT
                elif TABNO == 3:
                    MODE = 'h' # TAB_HISTORY
                elif TABNO == 4:
                    MODE = 'd' # TAB_DETAILS
                if TABNO < 5:
                    DISPTO = 0

    # Look for and process keyboard events to change modes.
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            # On 'q' or keypad enter key, quit the program.
            if ((event.key == K_KP_ENTER) or (event.key == K_q)):
                RUNNING = False

            # On '1' key (unshifted !, set mode to 'alert'.
            elif event.key == K_1:
                MODE = '!'
                DISPTO = 0

            # On 'w' key, set mode to 'weather'.
            elif event.key == K_w:
                MODE = 'w'
                DISPTO = 0

            # On 's' key, save a screen shot.
            elif event.key == K_s:
                MYDISP.screen_cap()

            # On 'a' key, set mode to 'almanac'.
            elif event.key == K_a:
                MODE = 'a'
                DISPTO = 0

            # On 'h' key, set mode to 'history'
            elif event.key == K_h:
                MODE = 'h'
                DISPTO = 0

            # On 'd' key, set mode to 'details'
            elif event.key == K_d:
                DETAILS_DAY = 0
                MODE = 'd'
                DISPTO = 0

    # Automatically switch back to weather display after a minute
    if MODE != 'w':
        DISPTO += 1
        if DISPTO > 600:   # One minute timeout at 100ms loop rate.
            MODE = 'w'
    else:
        DISPTO = 0
        # Look for mouse clicks on the forecast windows to display details
        MOUSE = pygame.mouse.get_pos()
        CLICK = pygame.mouse.get_pressed()
        if CLICK[0] == 1: # mouse click in 'weather' mode, might be a forecast button
            # Not straight forward, but I'm relying on all buttons being the same width
            # and it is faster than the straight forward ways.
            if MOUSE[1] > FORECAST_BUTTONS[0][1]: # below the top of the row of buttons
                if MOUSE[1] < FORECAST_BUTTONS[0][1] + FORECAST_BUTTONS[0][3]:
                    # above bottom of the row of buttons
                    BUT = math.trunc(MOUSE[0] / FORECAST_BUTTONS[0][2]) # modulo button width
                    if BUT < 4:
                        DETAILS_DAY = BUT
                        MODE = 'd'

    # Alert Display Mode
    if MODE == '!':
        # Update / Refresh the display after each second.
        if SECS != time.localtime().tm_sec:
            SECS = time.localtime().tm_sec
            MYDISP.disp_alert()

    # Weather Display Mode
    if MODE == 'w':
        # Update / Refresh the display after each second.
        if SECS != time.localtime().tm_sec:
            SECS = time.localtime().tm_sec
            MYDISP.disp_weather()
        # Every ten minutes, update the weather from the net.
        if (time.localtime().tm_min % 10 == 0) and (time.localtime().tm_sec == 0):
            MYDISP.updateweather()
            updateinsidedata()
            furnacefancontrol()
            adjusttstatsetting(MYDISP.temps[0][0])

    # History display mode
    if MODE == 'h':
        MYDISP.disp_history()

    # Details display mode
    if MODE == 'd':
        MYDISP.disp_details(DETAILS_DAY) # today by default

    # Almanac display mode
    if MODE == 'a':
        # Pace the screen updates to once per second.
        if SECS != time.localtime().tm_sec:
            SECS = time.localtime().tm_sec

            (INDAYLIGHT, DAYHRS, DAYMINS, TDAYLIGHT, TDARKNESS) = daylight(MYDISP.sunrise)

            # Stat Screen Display.
            MYDISP.disp_almanac(INDAYLIGHT, DAYHRS, DAYMINS, TDAYLIGHT, TDARKNESS)
        # Refresh the weather data every ten minutes
        if (time.localtime().tm_min % 10 == 0) and (time.localtime().tm_sec == 0):
            MYDISP.updateweather()

    (INDAYLIGHT, DAYHRS, DAYMINS, TDAYLIGHT, TDARKNESS) = daylight(MYDISP.sunrise)

    # Loop timer.
    pygame.time.wait(100)


pygame.quit()
