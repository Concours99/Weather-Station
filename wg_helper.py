""" Helper routines I find useful for most of my python code"""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions common to my code
#
# All functions, variables, etc. should start with "WG" so as not to interfere with other
# packages.
import datetime
import pprint

WG_HELPER_VERSION = "2.01"

###############################################################################
#
# Print out a trace message and flush the buffers.
#
def wg_trace_print(message, trace):
    """ Print out a tracing message."""
    if trace:
        today = datetime.datetime.now()
        outstring = (today.strftime("%x %X") + " - " + message)
        print(outstring, flush=True)

###############################################################################
#
# Print out an error message and flush the buffers.
#
def wg_error_print(where, message):
    """Print out an error message."""
    outstring = "Error in " + where + "! " + message
    wg_trace_print(outstring, True)

###############################################################################
#
# Print out a structure if we're tracing
#
def wg_trace_pprint(struct, trace):
    """Nicely print out a structure if we're tracing"""
    if trace:
        pprt = pprint.PrettyPrinter(indent=4)
        pprt.pprint(struct)
