#!/bin/bash
cd /home/pi/Weather
/usr/bin/python3 weather.py >> err.txt 2>&1 &

