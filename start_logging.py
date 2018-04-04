# Start logging.
#
# This will write to memory (whether it's clean or not).
# It also sets the RTC before logging.
#
# TODO:
#   get calibration eeprom
#
# 0.2s, 1s, 60s
#
# Will reset config file
# May add vbatt_pre and start_logging_time
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import time, json, sys, logging
from os import makedirs
from os.path import join, exists
from serial import Serial
from set_rtc import set_rtc_aligned, read_rtc, ts2dt
from common import is_logging, stop_logging, probably_empty, get_logging_config, read_vbatt, get_flash_id, get_logger_name, InvalidResponseException


logging.basicConfig(level=logging.WARNING)


DEFAULT_PORT = '/dev/ttyS0'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT))
if '' == PORT:
    PORT = DEFAULT_PORT

MAX_RETRY = 10


with Serial(PORT, 115200, timeout=1) as ser:

    try:
        logger_name = get_logger_name(ser)
        flash_id = get_flash_id(ser)
        print('Name: ' + logger_name)
        print('ID: ' + flash_id)
    except InvalidResponseException:
        logging.error('Cannot find logger. Terminating.')
        sys.exit()


    # Prepare config file
    makedirs(join('data', flash_id), exist_ok=True)
    if exists(join('data', flash_id, flash_id + '.config')):
        r = input('Found existing config file. Overwrite? (yes/no; default=yes)').strip()
        if r.lower() not in ['yes', '']:
            print('No change made. Terminating.')
            sys.exit()


    # Stop logging if necessary
    logging.debug('Stop ongoing logging if necessary...')
    try:
        if is_logging(ser):
            r = input('Logger is still logging. Stop it first? (yes/no; default=yes)')
            if r.strip().lower() in ['yes', '']:
                if not stop_logging(ser, maxretry=20):
                    logging.error('Logger is still logging and is not responding to stop_logging. Terminating.')
                    sys.exit()
            else:
                logging.error('Logger must be stopped before it can be restarted. Terminating.')
                sys.exit()
    except InvalidResponseException:
        logging.error('Cannot verify logger status. Terminating.')
        sys.exit()

    # Verify that it is indeed not logging
    assert not is_logging(ser)


    # Turn off LEDs
    ser.write(b'red_led_off green_led_off blue_led_off')


    # Set RTC to current UTC time
    print('Setting logger clock to current UTC time... ', end='', flush=True)
    cool = False
    for i in range(MAX_RETRY):
        device_time = set_rtc_aligned(ser)
        if abs(device_time - time.time()) <= 5:    # really should be <2s
            cool = True
            break
    if not cool:
        logging.error('Cannot set logger clock. Terminating.')
        sys.exit()
    print(' {}'.format(ts2dt(device_time)))


    # Set sample interval
    while True:
        print('Pick a sampling interval (subject to battery capacity):\n  A. 0.2 second (~43 hours)\n  B. 1 second (~9 days; default)\n  C. 60 second (~530 days)')
        r = input('Your choice: ')
        r = r.strip().lower()
        if r in ['a', 'b', 'c']:
            break
        if '' == r:
            r = 'b'
            break


    # a numeric code, not in real time unit
    # check the C definitions for the code-to-second mapping
    # internally, logger uses {0,1,2...}
    logging_interval_code = int(ord(r) - ord('a'))

    cool = False
    ser.write('set_logging_interval{}\n'.format(logging_interval_code).encode())
    for i in range(MAX_RETRY):
        c = get_logging_config(ser)
        if c['logging_interval_code'] == logging_interval_code:
            cool = True
            break
    if not cool:
        print('Could not set sampling interval. Terminating.')
        sys.exit()

    if not probably_empty(ser):
        print('(Memory is not clean.)')

    while True:
        r = input('Wipe memory? (yes/no; default=yes)')
        if r in ['', 'yes', 'no']:
            break
    if r.strip().lower() in ['yes', '']:        # anything else is considered a no (don't wipe).
        ser.write(b'clear_memory')
        for i in range(440):
            try:
                line = ser.read(100)
                print(line.decode(), end='', flush=True)
                if 'done.' in line.decode():
                    break
            except UnicodeDecodeError:
                pass

    #run = int(round(time.time()))
    # TODO: should store run number in logger so stop script can correlate start and stop configs
    # Basically a UUID for every logging session
    vbatt = read_vbatt(ser)

    cool = False
    for i in range(MAX_RETRY):
        ser.write(b'start_logging')
        time.sleep(0.1)
        if is_logging(ser):
            cool = True
            break
        else:
            logging.debug('... still logging...')

    if not cool:
        logging.error('Logger refuses to start. Terminating.')
        sys.exit()

    # Record metadata

    tmp = get_logging_config(ser)
    logging_start_time = tmp['logging_start_time']
    
    config = {'start_logging_time':time.time(),
              'flash_id':flash_id,
              'logger_name':logger_name,
              'logging_start_time': logging_start_time,
              'logging_interval_code': logging_interval_code,
              'vbatt_pre': vbatt,
              }
    
    config = json.dumps(config, separators=(',',':'))
    logging.debug(config)

    fn = '{}_{}.config'.format(flash_id, logging_start_time)
    fn = join('data', flash_id, fn)
    open(fn, 'w', 1).write(config)

    '''print('Ctrl + C to terminate...')
    with open('serial_log_{}.txt'.format(flash_id), 'w', 1) as fout:
        while True:
            try:
                line = ser.readline()
                if len(line):
                    line = line.decode()
                    print(line.strip())
                    fout.write(line)
            except KeyboardInterrupt:
                break
            except:
                pass'''
            
#input('Done. Hit RETURN to exit.')
print('Done.')
