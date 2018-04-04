# Print metadata of attached logger.
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import time, logging
from serial import Serial
from common import get_logger_name, get_flash_id, read_vbatt, is_logging, get_logging_config, InvalidResponseException
from set_rtc import read_rtc, ts2dt


logging.basicConfig(level=logging.WARNING)


DEFAULT_PORT = '/dev/ttyS0'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT)).strip()
if '' == PORT:
    PORT = DEFAULT_PORT


with Serial(PORT, 115200, timeout=1) as ser:
    while True:
        try:
            name = get_logger_name(ser)
            flash_id = get_flash_id(ser)
            running = is_logging(ser)
            vbatt = read_vbatt(ser)
            rtc = read_rtc(ser)
            r = get_logging_config(ser)
            logging_start_time = r['logging_start_time']
            logging_stop_time = r['logging_stop_time']

            running = 'Logging' if running else 'Not logging'

            if logging_start_time > 0:
                if logging_stop_time > logging_start_time:
                    r = 'Contains data from {} to {}'.format(ts2dt(logging_start_time), ts2dt(logging_stop_time))
                else:
                    r = 'Contains data from {} (no stop record)'.format(ts2dt(logging_start_time))
            else:
                r = 'No existing data.'

            print('NAME="{}" ID={} RTC={}, BATTERY={:.2f}V. {}. {}'.format(name, flash_id, ts2dt(rtc), vbatt, running, r))

            time.sleep(1)
            
        except (InvalidResponseException, UnicodeDecodeError, ValueError, IndexError) as e:
            logging.exception('')
            time.sleep(1)
