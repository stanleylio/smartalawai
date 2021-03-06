# Start a new logging session.
#
# If logger is already running, it offers the option to stop it first.
# If logger memory is not empty, it won't start a new session unless it's wiped.
# If logger memory is empty, it no longer prompt for wiping memory.
# It sets the logger's clock before logging.
#
# TODO:
#   get calibration eeprom
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import time, json, sys, logging
from os import makedirs
from os.path import join, exists
from serial import Serial
from kiwi import Kiwi
from common import ts2dt


logging.basicConfig(level=logging.WARNING)


MAX_RETRY = 10


def select_interval(kiwi, use_light_sensors):
    logging_interval_code = None
    
    # Set sample interval
    if 0 == kiwi._version:
        choices = ['A. 0.2 second (~43 hours)',
                   'B. 1 second (~9 days)',
                   'C. 60 seconds (~17 months; battery-limited)',
                   ]
        default = 1
        print('Pick a sampling interval:')
        for k,choice in enumerate(choices):
            print('  {}'.format(choice) + ('; DEFAULT' if k == default else ''))
        r = input('Your choice: ').strip().lower()
        if r in ['a', 'b', 'c', '']:    # '' if default
            # a numeric code, not in any real time unit
            # check the C definitions for the code-to-second mapping
            # internally, logger uses {0,1,2...}
            logging_interval_code = {'a':200,
                                     'b':1000,
                                     'c':60000,
                                     '':1000}.get(r, None)
    else:
        if use_light_sensors:
            # 65536 pages, 256 bytes per page, 4+4+2+2+2+2+2+2 bytes per sample (with light)
            # max. number of measurements = 65536*(256//20)
            choices = ['A. 0.25 second (~54 hours)',
                       'B. 0.5 second (~4.5 days)',
                       'C. 1 second (~9 days)',
                       'D. 5 seconds (~45 days)',
                       'E. 10 seconds (~3 months)',
                       'F. 30 seconds (~9 months; battery-limited)',
                       'G. 60 seconds (~17 months; battery-limited)',
                       ]
            default = 3
            print('Pick a sampling interval:')
            for k,choice in enumerate(choices):
                print('  {}'.format(choice) + ('; DEFAULT' if k == default else ''))
            r = input('Your choice: ').strip().lower()
            logging_interval_code = {'a':250,
                                     'b':500,
                                     'c':1000,
                                     'd':5000,
                                     'e':10000,
                                     'f':30000,
                                     'g':60000,
                                     '':5000}.get(r, None)
        else:
            # not using light sensors
            # 65536 pages, 256 bytes per page, 4+4 bytes per sample (without light)
            # max. number of measurements = 65536*(256//8)
            choices = ['A. 0.25 second (~6 days)',
                       'B. 0.5 second (~12 days)',
                       'C. 1 second (~24 days)',
                       'D. 5 seconds (~4 months)',
                       'E. 10 seconds (~8 months; battery-limited)',
                       'F. 30 seconds (~2 years; battery-limited)',
                       ]
            default = 3
            print('Pick a sampling interval:')
            for k,choice in enumerate(choices):
                print('  {}'.format(choice) + ('; DEFAULT' if k == default else ''))
            r = input('Your choice: ').strip().lower()
            logging_interval_code = {'a':250,
                                     'b':500,
                                     'c':1000,
                                     'd':5000,
                                     'e':10000,
                                     'f':30000,
                                     '':1000}.get(r, None)

    return logging_interval_code


def clear_memory(ser):
    ser.write(b'clear_memory')
    THRESHOLD = 8
    cool = THRESHOLD
    while cool > 0:
        try:
            line = ser.read(100)
            logging.debug(line)
            if not all([ord(b'.') == tmp for tmp in line]):
                logging.debug('Not cool')
                cool -= 1
            else:
                logging.debug('cool')
                cool = THRESHOLD

            print(line.decode(), end='', flush=True)
            if 'done.' in line.decode():
                return True
        except UnicodeDecodeError:
            pass

    if cool <= 0:
        return False


if '__main__' == __name__:

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

        kiwi = Kiwi(ser)
        
        try:
            config = kiwi.get_config(use_cached=True)
            logger_name = config['name']
            flash_id = config['id']
            vbatt = kiwi.get_battery_voltage()
            print('Logger "{}" (ID={}); battery voltage={:.1f} V'.format(logger_name, flash_id, vbatt))
            if vbatt < 2.2:
                print('WARNING: Battery voltage is low.')
        except:
            logging.exception('Cannot find logger. ABORT.')
            sys.exit()

        # Stop logging if necessary
        logging.debug('Stop ongoing logging if necessary...')
        if kiwi.is_logging():
            r = input('Logger is already logging. Stop it first? (yes/no; DEFAULT=no)')
            if r.strip().lower() in ['yes']:
                kiwi.stop_logging()
                if kiwi.is_logging():
                    print('Logger is not responding to stop_logging. ABORT.')
                    sys.exit()
            else:
                print('Logger must be stopped before it can be restarted. ABORT.')
                sys.exit()

        # Verify that it is indeed not logging
        assert not kiwi.is_logging()

        # Turn off LEDs
        ser.write(b'red_led_off green_led_off blue_led_off' if 0 == kiwi._version else b'roffgoffboff')

        if 0 == kiwi._version:
            # Set RTC to current UTC time
            print('Synchronizing clock to UTC...', flush=True)
            for i in range(MAX_RETRY):
                device_time = kiwi.set_rtc_aligned()
                if abs(device_time - time.time()) <= 2:
                    break
            else:
                print('Cannot set logger clock. Terminating.')
                sys.exit()
            print('Logger time: {} ({} UTC)'.format(ts2dt(device_time, utc=False), ts2dt(device_time, utc=True)))

        if 0 == kiwi._version:
            use_light_sensors = True
        else:
            while True:
                r = input('Use light sensors? (yes/no; default=yes)').strip().lower()
                if r in ['', 'yes', 'no']:
                    use_light_sensors = r not in ['no']
                    break

            for i in range(MAX_RETRY):
                ser.write(b'enable_light_sensors' if use_light_sensors else b'disable_light_sensors')
                if 'OK' == ser.readline().strip():
                    break

        logging_interval_code = None
        while logging_interval_code is None:
            logging_interval_code = select_interval(kiwi, use_light_sensors)

        for i in range(MAX_RETRY):
            if kiwi.set_logging_interval(logging_interval_code):
                break
        else:
            print('Could not set sampling interval. ABORT.')
            sys.exit()

        # Check if memory is empty

        is_memory_empty = kiwi.find_last_used_page() is None

        if not is_memory_empty:
            print('Memory is not empty.')
            while True:
                r = input('Wipe memory? (yes/no; default=no)').strip().lower()
                if r in ['', 'yes', 'no']:
                    break
            if r in ['yes']:
                logging.debug('User wants to wipe memory.')
                if not clear_memory(ser):
                    print('Logger is not responding to clear_memory. ABORT.')
                    sys.exit()
            else:
                # anything else is considered a NO (don't wipe).
                print('Logger cannot start if memory is not empty. ABORT.')
                sys.exit()

        # TODO: should store run number in logger so stop script can correlate start and stop configs
        # Basically a UUID for every logging session

        print('Attempting to start logging...')
        for i in range(MAX_RETRY):
            if kiwi.start_logging():
                break
        else:
            print('Logger refuses to start. ABORT.')
            sys.exit()

        print('Logger is running.')

        # Record config
        config = kiwi.get_config(use_cached=False)
        config['vbatt_pre'] = kiwi.get_battery_voltage()
        
        fn = join('data', config['id'])
        if not exists(fn):
            makedirs(fn)
        fn = join(fn, '{}_{}.config'.format(config['id'], config['start']))
        json.dump(config, open(fn, 'w', 1), separators=(',', ':'))
        print('Config file saved to {}'.format(fn))
