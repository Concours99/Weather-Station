#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions common to my code
#
# All functions, variables, etc. should start with "WG" so as not to interfere with other
# packages.

WGHelper_version = "1.0"

import datetime

###############################################################################
#
# Print out a trace message and flush the buffers.
#
def wg_trace_print(message, TRACE):
    if TRACE:
        today = datetime.datetime.now()
        outstring = (today.strftime("%x %X")
                     + " - "
                     + message)
        print(outstring, flush=True)

###############################################################################
#
# Print out an error message and flush the buffers.
#
def wg_error_print(where, message) :
    outstring = "Error in " + where + "! " + message
    wg_trace_print(outstring, True)

###############################################################################
#
# Print out a trace message and flush the buffers.
#
def wg_trace_pprint(message, TRACE):
    if TRACE:
        today = datetime.datetime.now()
        outstring = (today.strftime("%x %X")
                     + " - "
                     + message)
        print(outstring, flush=True)
        
