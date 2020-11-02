# fun with LEDs
#
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import time
from itertools import cycle
from serial import Serial
from kiwi import Kiwi


# find the serial port to use from user, from history, or make a guess
# if on Windows, print the list of COM ports
from common import serial_port_best_guess, save_default_port
DEFAULT_PORT = serial_port_best_guess(prompt=True)
PORT = input('PORT=? (default={}):'.format(DEFAULT_PORT)).strip()
# empty input, use default
if '' == PORT:
    PORT = DEFAULT_PORT

with Serial(PORT, 115200, timeout=1) as ser:

    save_default_port(PORT)
    
    kiwi = Kiwi(ser)

    if 0 == kiwi._version:
        cmds = cycle(['red_led_on', 'red_led_off', 'green_led_on', 'green_led_off', 'blue_led_on', 'blue_led_off'])
    else:
        cmds = cycle(['ron', 'roff', 'gon', 'goff', 'bon', 'boff'])

    while True:
        try:
            ser.write(next(cmds).encode())
            time.sleep(0.1)
        except KeyboardInterrupt:
            ser.write(b'red_led_off green_led_off blue_led_off roff goff boff')
            break
