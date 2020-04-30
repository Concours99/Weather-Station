# pylint: disable=w0613

"""Routines to query and control Radio Thermostat WiFi thermostat"""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a Radio Thermostat
import datetime
import pprint
import json
from urllib3 import PoolManager
from wg_helper import wg_error_print
from wg_helper import wg_trace_print

WG_RADIO_THERMOSTAT_VERSION = "2.1"

# The name (URL) of your Radio Thermostat
TSTAT_IP = "thermostat-76-8C-C9"
# fmode = fan mode
FAN_AUTO = 0
FAN_CIRC = 1
FAN_ON = 2
# tmode = thermostat mode
TMODE_OFF = 0
TMODE_HEAT = 1
TMODE_COOL = 2
TMODE_AUTO = 3
# mode = save energy mode
SAVE_ENERGY_MODE_DISABLE = 0
SAVE_ENERGY_MODE_ENABLE = 1
# hold = target temperature hold
HOLD_DISABLED = 0
HOLD_ENABLED = 1
# intensity = nightlight values
NIGHTLIGHT_OFF = 0
NIGHTLIGHT_ON = 4

RADTHERM_FLOAT_ERROR = -999.0
RADTHERM_FLOAT_SUCCESS = 999.0
RADTHERM_INT_ERROR = -999
RADTHERM_INT_SUCCESS = 999
RADTHERM_STR_ERROR = "ERROR"
RADTHERM_STR_SUCCESS = "SUCCESS"
RADTHERM_STATUS_ERROR = {"error" : -1}
RADTHERM_STATUS_SUCCESS = {"success" : 0}

###############################################################################
#
# Get the status of the thermostat.  This includes:
#   temp = current displayed air temp
#   tmode = thermostat operating mode (off, heat, cool, auto)
#   fmode = fan operating mode (auto, auto/circulate, on)
#   override = target temp temporary override (boolean)
#   hold = target temp hold status (boolean)
#   t_heat = temporary target heat setpoint
#   program_mode = program mode (Program A, Program B, Vacation, Holiday)
#   tstate = HVAC operating state (off, heat, cool)
#   fstate = fan operating state (boolean)
#   time = json object containing day of week, hour, minute
#   t_type_post = target temp post type (deprecated, do not use)
#
def radtherm_status():
    """Return the status of the thermostat"""
    try:
        pman = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat'
        ret = pman.request('GET', url)
        retval = json.loads(ret.data.decode('utf-8'))
        if 'error' in retval:
            wg_error_print("radtherm_status", " Unsuccessful status request (error)")
            return RADTHERM_STATUS_ERROR
        return retval
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_status", " Unsuccessful status request (exception)")
        return RADTHERM_STATUS_ERROR


###############################################################################
#
# Make a call to the thermostat to get a floating point data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       temp = current temperature
#   trace = true or false, print trace messages
#
def radtherm_get_float(what, trace):
    """Get the value of a piece of floating point data from the thermostat"""
    try:
        if what == "temp":
            resource = "temp"
        elif what == "humidity":
            resource = "humidity"
        elif what == "t_heat":
            resource = ""
        else:
            wg_error_print("radtherm_get_float", " Invalid 'what' argument " + what)
            return RADTHERM_FLOAT_ERROR
        pman = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat/' + resource
        ret = pman.request('GET', url)
        retval = json.loads(ret.data.decode('utf-8'))
        if trace:
            pprt = pprint.PrettyPrinter(indent=4)
            pprt.pprint(retval)
            wg_trace_print(what + " is " + str(retval[what]), trace)
        return retval[what]
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_get_float", " Unsuccessful GET request (exception) of " + what)
        return RADTHERM_FLOAT_ERROR


###############################################################################
#
# Make a call to the thermostat to get an integer data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       fmode = fan mode
#       tmode = thermostat operating mode (see above for values)
#       mode = Save Energy mode
#       hold = Target temperature hold status (see above for values)
#   trace = true or false, print trace messages
#
def radtherm_get_int(what, trace):
    """Get the value of a piece of integer data from the thermostat"""
    try:
        if what in ("fmode", "tmode", "hold"):
            resource = what
        elif what == "mode":
            resource = "save_energy/"
        else:
            wg_error_print("radtherm_get_int", " Invalid 'what' argument " + what)
            return RADTHERM_INT_ERROR
        pman = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat/' + resource
        ret = pman.request('GET', url)
        retval = json.loads(ret.data.decode('utf-8'))
        if trace:
            pprt = pprint.PrettyPrinter(indent=4)
            pprt.pprint(retval)
            wg_trace_print(what + " is " + str(retval[what]), trace)
        return retval[what]
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_get_int", " Unsuccessful GET request (exception) of " + what)
        return RADTHERM_INT_ERROR


###############################################################################
#
# Make a call to the thermostat to set afloating point data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       t_heat = target temperature (see above for valid values)
#   value = what to set it to
#   trace = true or false, print trace messages
#
def radtherm_set_float(what, value, trace):
    """Set the value of a piece of floating point data from the thermostat"""
    try:
        if what != "t_heat":
            wg_error_print("radtherm_set_float", " Invalid 'what' argument " + what)
            return RADTHERM_FLOAT_ERROR
        pman = PoolManager()
        encoded_body = json.dumps({what: value})
        ret = pman.request_encode_url('POST', 'http://' + TSTAT_IP +'/tstat',
                                      headers={'Content-Type': 'application/json'},
                                      body=encoded_body)
        retval = json.loads(ret.data.decode('utf-8'))
        if 'success' not in retval:
            wg_error_print("radtherm_set_float", " Unsuccessful POST request (error) of " + what)
            return RADTHERM_FLOAT_ERROR
        return RADTHERM_FLOAT_SUCCESS
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_set_float", " Unsuccessful POST request (exception) of " + what)
        return RADTHERM_FLOAT_ERROR


###############################################################################
#
# Make a call to the thermostat to set an integer data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       fmode = fan mode (see above for valid values)
#       mode = Save Energy mode
#       hold = Target temperature hold status (see above for values)
#       intensity = night light value (0 - 4)
#   value = what to set it to
#   trace = true or false, print trace messages
#
def radtherm_set_int(what, value, trace):
    """Set the value of a piece of integer data from the thermostat"""
    try:
        if what in ("fmode", "tmode", "hold"):
            resource = ""
        elif what == "mode":
            resource = "/save_energy"
        elif what == "intensity":
            resource = "/night_light"
        else:
            wg_error_print("radtherm_set_int", " Invalid 'what' argument " + what)
            return RADTHERM_INT_ERROR
        pman = PoolManager()
        encoded_body = json.dumps({what: value})
        ret = pman.request_encode_url('POST', 'http://' + TSTAT_IP + '/tstat' + resource,
                                      headers={'Content-Type': 'application/json'},
                                      body=encoded_body)
        retval = json.loads(ret.data.decode('utf-8'))
        if 'success' not in retval:
            wg_error_print("radtherm_set_int", " Unsuccessful POST request (error) of " + what)
            return RADTHERM_INT_ERROR
        return RADTHERM_INT_SUCCESS
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_set_int", " Unsuccessful POST request (exception) of " + what)
        return RADTHERM_INT_ERROR


###############################################################################
#
# Make a call to the thermostat to set a string data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       uma_line0 = line 0 of the user message area
#       uma_line1 - line 1 of the user message area
#   value = what to set it to
#   trace = true or false, print trace messages
#
def radtherm_set_str(what, value, trace):
    """Set the value of a piece of string data from the thermostat"""
    try:
        if what == "uma_line0":
            line = 0
            resource = '/uma'
        elif what == "uma_line1":
            line = 1
            resource = '/uma'
        else:
            wg_error_print("radtherm_set_str", " Invalid 'what' argument " + what)
            return RADTHERM_STR_ERROR
        pman = PoolManager()
        encoded_body = json.dumps({"line": line, "message": value})
        ret = pman.request_encode_url('POST', 'http://' + TSTAT_IP + '/tstat' + resource,
                                      headers={'Content-Type': 'application/json'},
                                      body=encoded_body)
        retval = json.loads(ret.data.decode('utf-8'))
        if 'success' not in retval:
            wg_error_print("radtherm_set_str", " Unsuccessful POST request (error) of " + what)
            return RADTHERM_STR_ERROR
    except Exception: #pylint: disable=W0703
        wg_error_print("radtherm_set_str", " Unsuccessful POST request (exception) of " + what)
        return RADTHERM_STR_ERROR
    return RADTHERM_STR_SUCCESS


###############################################################################
#
# Return the lowest temperature in today's program
# Args:
#   trace = true or false, print trace messages
#
def radtherm_get_todays_lowest_setting(trace):
    """Figure out the lowest temp setting in today's program."""
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    num_tries = 1
    retval = {}
    prog = RADTHERM_FLOAT_ERROR
    try:
        pman = PoolManager()
        wkdy = datetime.datetime.today().weekday()
        url = 'http://' + TSTAT_IP +'/tstat/program/heat/' + days[wkdy]
        while num_tries < 6 and retval.get(str(wkdy), 'error') == 'error':
            ret = pman.request('GET', url)
            retval = json.loads(ret.data.decode('utf-8'))
            if trace:
                pprt = pprint.PrettyPrinter(indent=4)
                pprt.pprint(retval)
            if retval.get(str(wkdy), 'error') != 'error':
                prog = min((retval[str(wkdy)])[1::2]) # 1,3,5, etc. elements are temps
            num_tries += 1
        return prog
    except Exception as err: #pylint: disable=W0703
        wg_error_print("radtherm_get_todays_highest_setting",
                       str(err))
        wg_error_print(err.response.text)
        return prog


###############################################################################
#
# Return the highest temperature in today's program
# Args:
#   trace = true or false, print trace messages
#
def radtherm_get_todays_highest_setting(trace):
    """Figure out the highest temp setting in today's program."""
    days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    num_tries = 1
    retval = {}
    prog = RADTHERM_FLOAT_ERROR
    try:
        pman = PoolManager()
        wkdy = datetime.datetime.today().weekday()
        url = 'http://' + TSTAT_IP +'/tstat/program/heat/' + days[wkdy]
        while num_tries < 6 and retval.get(str(wkdy), 'error') == 'error':
            ret = pman.request('GET', url)
            retval = json.loads(ret.data.decode('utf-8'))
            if trace:
                pprt = pprint.PrettyPrinter(indent=4)
                pprt.pprint(retval)
            if retval.get(str(wkdy), 'error') != 'error':
                prog = max((retval[str(wkdy)])[1::2]) # 1,3,5, etc. elements are the temps
            num_tries += 1
        return prog
    except Exception as err: #pylint: disable=W0703
        wg_error_print("radtherm_get_todays_highest_setting",
                       str(err))
        if hasattr('err', 'response'):
            wg_error_print(err.response.text)
        return prog
