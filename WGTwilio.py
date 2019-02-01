#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018, Wayne Geiser (geiserw@gmail.com).  All Rights Reserved
#
# Helper functiona and definitions to interface with a Twilio account

WGTwilio_version = "1.0"

from twilio.rest import Client

# SMS texting facility - requires a Twilio account
from TWAccountSettings import *

####################################################################
#
# Send a text message
#
def SendText(text_message) :
    client = Client(TWILIO_ACT, TWILIO_AUTH_TOKEN)
    client.messages.create(to = CELL_PHONE,
                            from_ = FROM_PHONE,
                            body = text_message)
