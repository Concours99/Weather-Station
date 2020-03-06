""" Helper routines I find useful for most of my python code"""
#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018-2020, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions common to my code
#
# All functions, variables, etc. should start with "WG" so as not to interfere with other
# packages.
import datetime
import pprint
from logzero import logger, logfile

WG_HELPER_VERSION = "2.02"

###############################################################################
#
# Initialize logging
#
def wg_init_log(file):
    """ Initialize the logfile.  Only 1MB file size. 3 rotations. """
    # always do this, even if not 'Trace'ing so we get errors
    logfile(file, maxBytes=1e6, backupCount=3)

###############################################################################
#
# Print out a trace message and flush the buffers.
#
def wg_trace_print(message, trace):
    """ Print out a tracing message."""
    if trace:
        logger.info(message)

###############################################################################
#
# Print out an error message and flush the buffers.
#
def wg_error_print(where, message):
    """Print out an error message."""
    logger.error(where + ": " + message)

###############################################################################
#
# Print out a structure if we're tracing
#
def wg_trace_pprint(struct, trace):
    """Nicely print out a structure if we're tracing"""
    if trace:
        pprt = pprint.PrettyPrinter(indent=4)
        logger.info(pprt.pformat(struct))
