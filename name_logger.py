# Give the logger a name.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import sys, time, logging
from serial import Serial
from kiwi import Kiwi

logging.basicConfig(level=logging.WARNING)

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

    if kiwi.is_logging():
        r = input('Cannot rename logger while it is running. Stop it? (yes/no; default=no)')
        if 'yes' == r.strip():
            kiwi.stop_logging()
        else:
            print('This script cannot proceed while logger is still running. Terminating.')
            sys.exit()

    try:
        config = kiwi.get_config(use_cached=True)
        print('Current logger name: "{}" (ID={})'.format(config['name'], config['id']))
    except UnicodeDecodeError:
        pass

    while True:
        newname = input('Enter new name (max. 15 characters): ')
        if len(newname) <= 15:
            break
    cool = False
    for _ in range(8):
        ser.write('set_logger_name{}\n'.format(newname).encode())
        time.sleep(0.5)
        if newname == kiwi.get_config(use_cached=False).get('name', None):
            cool = True
            break

    if cool:    
        print('Logger name set to "{}"'.format(newname))
    else:
        print('Could not rename logger. Terminating.')
    
