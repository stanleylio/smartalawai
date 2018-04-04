import sys, logging, time, json
from serial import Serial



PORT = 'COM18'

with Serial(PORT, 115200, timeout=1) as ser:

    # 625~1250
    # 625~938
    # 625~782
    # 704~782
    # 743~782
    # 763~782 (763, can recover)
    # 773~782 (773, can recover)
    # 782 takes a while to recover

    ser.write(('gibberish'*782).encode())

    #while True:
    #    ser.write(b'red_led_off red_led_on')

print('done.')
