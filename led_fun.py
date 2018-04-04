# fun with LEDs
#
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import time
from itertools import cycle
from serial import Serial


cmds = cycle(['red_led_on', 'red_led_off', 'green_led_on', 'green_led_off', 'blue_led_on', 'blue_led_off'])


DEFAULT_PORT = '/dev/ttyS0'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT)).strip()
if '' == PORT:
    PORT = DEFAULT_PORT


with Serial(PORT, 115200, timeout=1) as ser:

    while True:
        ser.write(next(cmds).encode())
        time.sleep(0.1)
