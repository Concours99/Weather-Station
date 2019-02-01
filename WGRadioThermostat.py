#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a Radio Thermostat

WGRadioThermostat_version = "1.01"

from urllib3 import PoolManager
import json
from urllib.request import urlretrieve, urlopen
import pprint

from WGHelper import *

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

RadTherm_float_ERROR = -999.0
RadTherm_int_ERROR = -999
RadTherm_str_ERROR = "ERROR"
RadTherm_status_ERROR = {"error" : -1}

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
def RadThermStatus(trace) :
    try:
        pm = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat'
        r = pm.request('GET', url)
        retval = json.loads(r.data.decode('utf-8'))
        if 'error' in retval :
            WGErrorPrint("RadThermStatus", " Unsuccessful status request (exception)")
            return RadTherm_status_ERROR
        else :
            return retval
    except :
        WGErrorPrint("RadThermStatus", " Unsuccessful status request (exception)")
        return RadTherm_status_ERROR
       
###############################################################################
#
# Make a call to the thermostat to get a floating point data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       temp = current temperature
#   trace = true or false, print trace messages
#
def RadThermGetFloat(what, trace) :
    try :
        if what == "temp" :
            resource = "temp"
        else :
            if what == "humidity" :
                resource = "humidity"
            else :
                if what == "t_heat" :
                    resource = ""
                else :
                    WGErrorPrint("RadThermGetFloat", " Invalid 'what' argument " + what)
                    return RadTherm_float_ERROR
        pm = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat/' + resource
        r = pm.request('GET', url)
        ht = json.loads(r.data.decode('utf-8'))
        if trace :
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(ht)
            WGTracePrint(what + " is " + str(ht[what]))
        return ht[what]
    except :
        WGErrorPrint("RadThermGetFloat", " Unsuccessful GET request (exception) of " + what)
        return RadTherm_float_ERROR

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
def RadThermGetInt(what, trace) :
    try :
        if (what == "fmode") or (what == "tmode") or (what == "hold") :
            resource = what
        else :
            if what == "mode" :
                resource = "save_energy/"
            else :
                WGErrorPrint("RadThermGetInt", " Invalid 'what' argument " + what)
                return RadTherm_int_ERROR
        pm = PoolManager()
        url = 'http://' + TSTAT_IP +'/tstat/' + resource
        r = pm.request('GET', url)
        ht = json.loads(r.data.decode('utf-8'))
        if trace :
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(ht)
            WGTracePrint(what + " is " + str(ht[what]))
        return ht[what]
    except :
        WGErrorPrint("RadThermGetInt", " Unsuccessful GET request (exception) of " + what)
        return RadTherm_int_ERROR

###############################################################################
#
# Make a call to the thermostat to set afloating point data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       t_heat = target temperature (see above for valid values)
#   value = what to set it to
#   trace = true or false, print trace messages
#
def RadThermSetFloat(what, value, trace) :
    try :
        if what == "t_heat" :
            resource = ""
        else :
            WGErrorPrint("RadThermSetFloat", " Invalid 'what' argument " + what)
        pm = PoolManager()
        encoded_body = json.dumps({what: value})
        r = pm.request_encode_url('POST', 'http://' + TSTAT_IP +'/tstat',
                                    headers={'Content-Type': 'application/json'},
                                    body=encoded_body)
        ht = json.loads(r.data.decode('utf-8'))
        if 'success' not in ht :
            WGErrorPrint("RadThermSetFloat", " Unsuccessful POST request of " + what)
            return RadTherm_float_ERROR
    except :
        WGErrorPrint("RadThermSetFloat", " Unsuccessful POST request (exception) of " + what)
        return RadTherm_float_ERROR

###############################################################################
#
# Make a call to the thermostat to set an integer data value.
# Args:
#   what = string of what data value you want.  Legal values include:
#       fmode = fan mode (see above for valid values)
#       mode = Save Energy mode
#       hold = Target temperature hold status (see above for values)
#   value = what to set it to
#   trace = true or false, print trace messages
#
def RadThermSetInt(what, value, trace) :
    try :
        if (what == "fmode") or (what == "tmode") or (what == "hold") :
            resource = ""
        else :
            if what == "mode" :
                resource = "/save_energy"
            else :
                WGErrorPrint("RadThermGetInt", " Invalid 'what' argument " + what)
                return RadTherm_int_ERROR
        pm = PoolManager()
        encoded_body = json.dumps({what: value})
        r = pm.request_encode_url('POST', 'http://' + TSTAT_IP + '/tstat' + resource,
                                    headers={'Content-Type': 'application/json'},
                                    body=encoded_body)
        ht = json.loads(r.data.decode('utf-8'))
        if 'success' not in ht :
            WGErrorPrint("RadThermSetInt", " Unsuccessful POST request of " + what)
            return RadTherm_int_ERROR
    except :
        WGErrorPrint("RadThermSetInt", " Unsuccessful POST request (exception) of " + what)
        return RadTherm_int_ERROR

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
def RadThermSetStr(what, value, trace) :
    try :
        if what == "uma_line0" :
            line = 0
            resource = '/uma'
        else :
            if what == "uma_line1" :
                line = 1
                resource = '/uma'
            else :
                WGErrorPrint("RadThermSet Str", " Invalid 'what' argument " + what)
                return RadTherm_str_ERROR
        pm = PoolManager()
        encoded_body = json.dumps({"line": line, "message": value})
        r = pm.request_encode_url('POST', 'http://' + TSTAT_IP + '/tstat' + resource,
                                    headers={'Content-Type': 'application/json'},
                                    body=encoded_body)
        ht = json.loads(r.data.decode('utf-8'))
        if 'success' not in ht :
            WGErrorPrint("RadThermSetStr", " Unsuccessful POST request of " + what)
            return RadTherm_str_ERROR
    except :
        WGErrorPrint("RadThermSetStr", " Unsuccessful POST request (exception) of " + what)
        return RadTherm_str_ERROR
        
               