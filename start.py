from kiwi import Kiwi
from common import serial_port_best_guess2, save_default_port, ts2dt, save_most_recent_id
import serial, time, logging, sys, json, random
from birdseye import birdseye_read, birdseye_plot
from start_logging import select_interval, clear_memory
from read_memory import read_memory
from bin2csv import bin2csv


if '__main__' == __name__:

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('kiwi').setLevel(logging.INFO)

    USE_UTC = False

    while True:
        try:
            L = serial_port_best_guess2()
            if 1 == len(L):
                port = L[0]
            elif len(L):
                print('Available port(s):')
                for port in L:
                    print('  ' + port)
                port = input('Which serial port to use? (default={})'.format(L[-1])).strip()
                port = port if len(port) else L[-1]
            else:
                port = input('Didn\'t find a serial port. Which serial port to use?').strip()

            # test it
            serial.Serial(port)
            break
        except serial.serialutil.SerialException:
            print(f'{port} is in use.')

    print(f'Using {port}')

    with serial.Serial(port, 115200, timeout=1) as ser:

        save_default_port(port)

        while True:
            try:
                if random.random() > 0.8:
                    print('Looking for a logger...')
                
                kiwi = Kiwi(ser)
                config = kiwi.get_config(use_cached=True)
                is_logging = kiwi.is_logging()

                print('Found "{}" (ID={}); battery: {:.1f} V; {}.'.format(config['name'],
                                                                         config['id'],
                                                                         kiwi.get_battery_voltage(),
                                                                         'LOGGING' if is_logging else 'not logging',
                                                                         ))

                if is_logging:
                    r = input("""
What would you like to do?
    1. See configuration
    2. Stop logging (!)
Your choice:
""").strip()
                    if '1' == r:
                        for k in config:
                            print('{}={}'.format(k,  config[k]))
                    elif '2' == r:
                        r = input("""Type "stop" then hit RETURN to confirm:""").strip().lower().replace('"', '')
                        if r == 'stop':
                            kiwi.stop_logging()

                else:   # not logging
                    r = input("""
What would you like to do?
    1. See configuration
    2. Show memory overview
    3. Read memory to file
    4. Configure logger
    5. Rename logger
    6. Clear memory
    7. Start logging now
Your choice:
""").strip()
                    if '1' == r:
                        for k in config:
                            print('{}={}'.format(k, config[k]))

                    elif '2' == r:
                        if kiwi.get_sample_count() <= 0:
                            print('Logger is empty.')
                        else:
                            D,STRIDE = birdseye_read(kiwi, 128)
                            birdseye_plot(D, STRIDE, config, kiwi.get_sample_count(), USE_UTC)

                    elif '3' == r:
                        fn_bin = read_memory(kiwi)
                        if fn_bin is not None:
                            fn_csv = fn_bin.rsplit('.')[0] + '.csv'
                            bin2csv(fn_bin, fn_csv, config)
                            save_most_recent_id(config['id'])
                            print('Output CSV file: {}'.format(fn_csv))
                            print('Output binary file: {}'.format(fn_bin))

                    elif '4' == r:
                        if 0 != kiwi._version:
                            while True:
                                r = input('Use light sensors? (yes/no; default=yes)').strip().lower()
                                if r in ['', 'yes', 'no']:
                                    use_light_sensors = r not in ['no']
                                    break

                            ser.write(b'enable_light_sensors' if use_light_sensors else b'disable_light_sensors')
                            ser.readline().strip()      # 'OK'
                        else:
                            use_light_sensors = True

                        interval = None
                        while interval is None:
                            interval = select_interval(kiwi, use_light_sensors)
                        kiwi.set_logging_interval(interval)

                    elif '5' == r:
                        newname = input('Enter new name (max. 15 characters):').strip()
                        if len(newname) > 15:
                            print('(The new name has been truncated.)')
                            newname = newname[:15]
                        ser.write('set_logger_name{}\n'.format(newname).encode())
                        time.sleep(0.5)
                        
                        print('Logger name set to "{}"'.format(kiwi.get_config()['name']))

                    elif '6' == r:
                        r = input('Type "clear" to confirm:')
                        if 'clear' == r.strip().replace('"', '').lower():
                            clear_memory(ser)
                        else:
                            print('No change was made.')

                    elif '7' == r:
                        # Turn off LEDs
                        #ser.write(b'red_led_off green_led_off blue_led_off' if 0 == kiwi._version else b'roffgoffboff')
                        ser.write(b'  reset')
                        time.sleep(1)

                        v = kiwi.get_battery_voltage()
                        print('Battery: {:.1f} V'.format(v))
                        if v <= 1.1:
                            print('WARNING: low battery ({:.1f}) V'.format(v))

                        device_time = kiwi.set_rtc_aligned()
                        print('Logger time: {} ({} UTC); delta={:.3f} s'.format(
                            ts2dt(device_time, utc=False),
                            ts2dt(device_time, utc=True),
                            time.time() - device_time
                            ))

                        count = kiwi.get_sample_count()
                        if count:
                            print('Can\'t start logging if memory is not empty.')
                        else:
                            kiwi.start_logging()
                            print('Logger is{} logging.'.format('' if kiwi.is_logging() else ' not'))

            except RuntimeError:
                print('(Logger not detected)')
            except Exception as e:
                logging.exception(e)
                #raise
                time.sleep(1)
