# Test the hardware of a logger.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import time, functools, sys, logging
sys.path.append('..')
from datetime import datetime
from serial import Serial
from kiwi import Kiwi
from common import serial_port_best_guess, save_default_port
from dev.set_rtc import set_rtc


logging.basicConfig(level=logging.WARNING)


print('Detected ports:')
DEFAULT_PORT = serial_port_best_guess(prompt=True)
PORT = input('Which one to use? (default={})'.format(DEFAULT_PORT)).strip()
# empty input, use default
if '' == PORT:
    PORT = DEFAULT_PORT
print(PORT)

with Serial(PORT, 115200, timeout=1) as ser:

    kiwi = Kiwi(ser)

    def f():
        try:
            t = kiwi.read_temperature()
            return t > 0 and t < 50
        except:
            logging.error('Logger\'s response: {}'.format(t))
            return False
    print('PASS' if f else 'FAIL! (temperature)')

    def f():
        try:
            p = kiwi.read_pressure()
            return p > 95 and p < 105
        except:
            logging.error('Logger\'s response: {}'.format(p))
            return False
    print('PASS' if f else 'FAIL! (pressure)')
    
    def f():
        try:
            lx = kiwi.read_light()
            return lx[0] >= 0 and lx[0] <= 130e3 \
                   and lx[1] >= 0 and lx[1] <= 130e3 \
                   and lx[2] >= 0 and lx[2] <= 0.25168*65535 \
                   and lx[3] >= 0 and lx[3] <= 0.25168*65535 \
                   and lx[4] >= 0 and lx[4] <= 0.25168*65535 \
                   and lx[5] >= 0 and lx[5] <= 0.25168*65535
        except:
            logging.error('Logger\'s response: {}'.format(lx))
            return False
    print('PASS' if f else 'FAIL! (light)')

    if 0 == kiwi._version:
        def f():
            try:
                return abs(time.time() - float(set_rtc(ser))) < 5
            except:
                return False
        print('PASS' if f() else 'FAIL! (RTC)')

    print('PASS' if kiwi.get_battery_voltage() > 2.0 else 'FAIL! (battery)')

    def f():
        try:
            # not foolproof, but takes little work.
            C = ['red', 'green', 'blue']
            good = True
            for k,c in enumerate(C):
                ser.write('{}_led_on'.format(c).encode())
                ser.write('{}on'.format(c[0]).encode())
                time.sleep(0.1)
                a = kiwi.read_light(as_dict=False)[k + 2]
                ser.write('{}_led_off'.format(c).encode())
                ser.write('{}off'.format(c[0]).encode())
                time.sleep(0.1)
                b = kiwi.read_light(as_dict=False)[k + 2]
                good &= a > 1.1*b

            return good
        except:
            return False
    print('PASS' if f() else 'FAIL! (rgbw)')

    def f():
        try:
            ser.write(b'red_led_on ron')
            ser.write(b'green_led_on gon')
            ser.write(b'blue_led_on bon')
            time.sleep(0.1)
            a = kiwi.read_light(as_dict=False)[0]

            ser.write(b'red_led_off roff')
            ser.write(b'green_led_off goff')
            ser.write(b'blue_led_off boff')
            time.sleep(0.1)
            b = kiwi.read_light(as_dict=False)[0]

            return a > 1.1*b
        except:
            return False
    print('PASS' if f() else 'FAIL! (ambient light)')


    '''ser.write(b'clear_memory')
    for _ in range(200):
        time.sleep(0.1)
        r = ser.readline().decode().strip()
        if len(r):
            print(r, end='')
        else:
            break'''

    def f():
        try:
            good = True
            
            kiwi.set_logging_interval(1000)
            if 0 == kiwi._version:
                ser.write(b'start_logging')
            else:
                ser.write('start_logging{}\r\n'.format(int(time.time())).encode('utf-8'))
                good &= 'OK' == ser.readline().decode().strip()
            
            good &= kiwi.is_logging()
            ser.write(b'stop_logging')
            if 0 != kiwi._version:
                good &= 'OK' == ser.readline().decode().strip()
            good &= not kiwi.is_logging()

            return good
        except:
            raise
            return False
    print('PASS' if f() else 'FAIL! (start_logging)')
