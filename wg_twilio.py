# pylint: disable=e0401

#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018-2019, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a Twilio account
"""Interface to a Twilio.com account"""
from twilio.rest import Client

# SMS texting facility - requires a Twilio account
from twilio_account_settings import TWILIO_ACT
from twilio_account_settings import TWILIO_AUTH_TOKEN
from twilio_account_settings import CELL_PHONE
from twilio_account_settings import FROM_PHONE

WG_TWILIO_VERSION = "2.0"

####################################################################
#
# Send a text message
#
def sendtext(text_message):
    """Send a text_message to the cell number in account settings file"""
    client = Client(TWILIO_ACT, TWILIO_AUTH_TOKEN)
    client.messages.create(to=CELL_PHONE,
                           from_=FROM_PHONE,
                           body=text_message)
