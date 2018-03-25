# Start logging.
#
# This will write to memory (whether it's clean or not).
# It also sets the RTC before logging.
#
# TODO:
#   WARN if memory is not empty
#   sampling rate
#   get calibration eeprom
#
# 0.2s, 1s, 60s, 600s, 3600s
#   for 60s+, burst of N
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import time, json
from serial import Serial
from set_rtc import set_rtc_aligned, read_rtc


DEFAULT_PORT = 'COM18'
PORT = input('PORT=? (default={})'.format(DEFAULT_PORT))
if '' == PORT:
    PORT = DEFAULT_PORT

with Serial(PORT, 115200, timeout=1) as ser:

    r = ''
    for i in range(10):
        ser.write(b'stop_logging')
        r = ser.readline().decode()
        #print(r)
        if 'Logging stopped' in r:
            break
    ser.write(b'red_led_off')
    ser.write(b'green_led_off')
    ser.write(b'blue_led_off')

    print('Setting device clock...')
    set_rtc_aligned(ser)
    print('Device clock: {}'.format(read_rtc(ser)))

    # TODO: check if memory is empty
    r = input('Wipe memory? (yes/no; default=no)')
    if r.strip().lower() == 'yes':
        ser.write(b'clear_memory')
        for i in range(400):
            line = ser.read(100)
            print(line.decode(), end='')
            if 'done.' in line.decode():
                break

    ser.write(b'spi_flash_get_unique_id')
    flash_id = ser.readline().decode().strip()
    #run = int(round(time.time()))
    # TODO: should store run number in logger so stop script can correlate start and stop configs
    with open('kiwi_config_{}.txt'.format(flash_id), 'w') as flog:
        ser.write(b'read_rtc')
        rtc_time = ser.readline().decode().strip()
        # todo: read Vbatt and Vcc

        ser.write(b'start_logging')
        start_time = time.time()

        config = {'start_time':start_time, 'flash_id':flash_id, 'rtc_time':rtc_time}
        config = json.dumps(config, separators=(',',':'))
        print(config)
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
            
print('Done.')
