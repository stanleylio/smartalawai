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
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import time, json, sys, logging
from serial import Serial
from set_rtc import set_rtc_aligned, read_rtc, ts2dt
from common import is_logging, stop_logging, probably_empty, get_logging_config, read_vbatt, get_flash_id


logging.basicConfig(level=logging.DEBUG)


DEFAULT_PORT = 'COM18'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT))
if '' == PORT:
    PORT = DEFAULT_PORT

MAX_RETRY = 10


with Serial(PORT, 115200, timeout=1) as ser:

    ser.write(b'get_logger_name')
    logger_name = ser.readline().decode().strip()
    flash_id = get_flash_id(ser)
    print('Logger name: ' + logger_name)
    print('Memory ID: ' + flash_id)


    # Stop logging if necessary
    logging.debug('Stop ongoing logging if necessary...')
    if is_logging(ser):
        r = input('Logger is still logging. Stop it first? (yes/no; default=yes)')
        if r.strip().lower() in ['yes', '']:
            if not stop_logging(ser):
                print('Logger is still logging and is not responding to stop_logging. Terminating.')
                sys.exit()
        else:
            print('Logger must be stopped before it can be restarted. Terminating.')
            sys.exit()

    # Verify that it is indeed not logging
    assert not is_logging(ser)


    # Turn off LEDs
    for i in range(2):
        ser.write(b'red_led_off green_led_off blue_led_off')

    # Setting RTC to current UTC time
    print('Setting logger clock to current UTC time... ', end='', flush=True)
    cool = False
    for i in range(MAX_RETRY):
        set_rtc_aligned(ser)
        device_time = read_rtc(ser)
        if abs(device_time - time.time()) <= 10:    # really should be <2s
            cool = True
            break
    if not cool:
        logging.error('Cannot set logger clock. Terminating.')
        sys.exit()
    print(' {}'.format(ts2dt(device_time)))


    # Set sample interval
    while True:
        print('Pick a sampling interval:\n  A. 0.2 second (~43 hours)\n  B. 1 second (>9 days; default)\n  C. 60 second (>500 days)')
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
        for i in range(402):
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
    with open('{}.config'.format(flash_id), 'w') as flog:
        # todo: read Vbatt and Vcc

        for i in range(MAX_RETRY):
            ser.write(b'start_logging')
            if is_logging(ser):
                break

        vbatt = read_vbatt(ser)

        config = {'start_logging_time':time.time(),
                  'flash_id':flash_id,
                  'logger_name':logger_name,
                  'logging_interval_code': logging_interval_code,
                  'vbatt_pre': vbatt,
                  }
        config = json.dumps(config, separators=(',',':'))
        logging.debug(config)
        flog.write(config)

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
            
input('Done. Hit RETURN to exit.')
