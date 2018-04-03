# Give the logger a name.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import sys, time
from serial import Serial
from common import get_logger_name, get_flash_id, is_logging, stop_logging


DEFAULT_PORT = 'COM18'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT))
if '' == PORT:
    PORT = DEFAULT_PORT


with Serial(PORT, 115200, timeout=1) as ser:
    try:
        if is_logging(ser):
            r = input('Cannot rename logger while it is running. Stop it? (yes/no; default=no)')
            if 'yes' == r.strip():
                stop_logging(ser)
            else:
                print('Terminating.')
                sys.exit()

        try:
            name = get_logger_name(ser)
            flash_id = get_flash_id(ser)
            
            print('Current logger name: {} (ID={})'.format(name, flash_id))
        except UnicodeDecodeError:
            pass

        name = ''
        while True:
            name = input('Enter new name (max. 15 characters): ')
            if len(name) <= 15:
                break

        if len(name) > 0:
            ser.write('set_logger_name{}\n'.format(name).encode())
        else:
            print('Empty input. Name unchanged.')
            sys.exit()
        
        name = get_logger_name(ser)
        print('Logger name set to "{}"'.format(name))
        
    except UnicodeDecodeError:
        pass
