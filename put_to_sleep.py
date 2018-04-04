# Continuously sends the "sleep" command.
# Point at a logger to put it to sleep.
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import time
from serial import Serial


DEFAULT_PORT = '/dev/ttyS0'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT)).strip()
if '' == PORT:
    PORT = DEFAULT_PORT


with Serial(PORT, 115200, timeout=0.1) as ser:
    while True:
        ser.write(b'sleep')
        try:
            r = ser.readline().decode().strip()
            if len(r):
                print(r)
        except UnicodeDecodeError:
            pass
        time.sleep(0.1)
