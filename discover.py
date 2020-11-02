# Search for loggers. Display their metadata if found. Only show newly found ones.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import time, logging, random
from serial import Serial
from kiwi import Kiwi
from common import ts2dt

logging.basicConfig(level=logging.DEBUG)

# find the serial port to use from user, from history, or make a guess
# if on Windows, print the list of COM ports
from common import serial_port_best_guess, save_default_port
print('Detected ports:')
DEFAULT_PORT = serial_port_best_guess(prompt=True)
print('- - -')
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT)).strip()
# empty input, use default
if '' == PORT:
    PORT = DEFAULT_PORT


with Serial(PORT, 115200, timeout=1) as ser:

    save_default_port(PORT)

    known_ids = set()

    while True:
        try:
            kiwi = Kiwi(ser)
            config = kiwi.get_config(use_cached=True)

            if config['id'] not in known_ids:
                known_ids.add(config['id'])
                print('Found "{}" (ID={}); battery={:.1f} V; {}.'.format(config['name'],
                                                                         config['id'],
                                                                         kiwi.get_battery_voltage(),
                                                                         'LOGGING' if kiwi.is_logging() else 'not logging',
                                                                         ))
            else:
                logging.debug('I have seen {} already.'.format(config['id']))

            time.sleep(1)
        except (UnicodeDecodeError, ValueError, IndexError, TypeError) as e:
            logging.debug(e)
        except RuntimeError:
            if random.random() > 0.8:
                print('[cricket sound]')
            time.sleep(1)
        except KeyboardInterrupt:
            break

        
