#
# Metadata:
# logger_name:              Logger's name given by user (maximum 15 characters).
# flash_id:                 Logger's unique hardware ID.
# logging_start_time:       Logger's RTC time when logging started. Recorded in EEPROM by logger.
# logging_stop_time:        Logger's RTC time when logging stopped. Recorded in EEPROM by logger. Read as 0 if logger is running, or if logging was stopped abnormally (power outage, reset).
# logging_interval_code:    Code representing sampling interval. A numeric code used internally by the firmware.
# start_logging_time:       User's computer time when logging started.
# stop_logging_time:        User's computer time if and when logging is stopped by user (absent if logger wasn't logging).
#
# interval codes: 0: 0.2s, 1: 1s, 2: 60s
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import logging, random, time, string, calendar, sys, json
import serial.tools.list_ports
from dev.crc_check import check_response
from datetime import datetime
from os.path import exists, join, dirname
import platform, glob, json
from os.path import exists, join, dirname


SAMPLE_INTERVAL_CODE_MAP = {0:1/5, 1:1, 2:60}
# W25Q128JV: 128Mb, or 16MB. 65536 of 256-byte pages. Min. erase size = 1 sector = 16 pages (4096 bytes)
SPI_FLASH_SIZE_BYTE = 16*1024*1024
SPI_FLASH_PAGE_SIZE_BYTE = 256


class InvalidResponseException(Exception):
    pass


def dt2ts(dt):
    return calendar.timegm(dt.timetuple()) + (dt.microsecond)*(1e-6)

def ts2dt(ts, *_, utc=True):
    if utc:
        return datetime.utcfromtimestamp(ts)
    else:
        return datetime.fromtimestamp(ts)

def list_serial_port():
    """ doesn't work on the pi. it doesn't show /dev/ttyS0"""
    return sorted(serial.tools.list_ports.comports(), key=lambda c: int(c.device.replace('COM', '')))

def serial_port_best_guess(prompt=False):
    P = platform.system()

    if 'Windows' in P:
        L = list_serial_port()
        if prompt:
            for c in L:
                print(c.description)

    # see if there's any hint
    try:
        fn = join(dirname(__file__), 'saw.tmp')
        if exists(fn):
            port = json.load(open(fn))['serialport']
            if 'Windows' in P:
                if port.lower() in [c.device.lower() for c in serial.tools.list_ports.comports()]:
                    return port
            else:
                if exists(port):
                    return port
    except Exception as e:
        logging.debug(e)

    # for whatever reason, no hint on which serial port to use
    if 'Windows' in P:
        return L[-1].device
    else:
        # cu.usbserial########
        # tty.usbserial########
        # tty.usbmodem########

        if exists('/dev'):
            L = glob.glob('/dev/ttyUSB*')       # mac, or pi with adapter
            if len(L):
                return L[-1]

            L = glob.glob('/dev/*usbserial*')   # still mac
            if len(L):
                return L[-1]

            L = glob.glob('/dev/*usbmodem*')       # mac again
            if '.' in L:
                return L[-1]

    return '/dev/ttyS0'

def serial_port_best_guess2():
    P = platform.system()

    # see if there's any hint
    hint = None
    try:
        fn = join(dirname(__file__), 'saw.tmp')
        if exists(fn):
            port = json.load(open(fn))['serialport']
            hint = port
    except Exception as e:
        logging.debug(e)

    if 'Windows' in P:
        L = [port.device for port in list_serial_port()]
    else:
        L = []
        # cu.usbserial########
        # tty.usbserial########
        # tty.usbmodem########

        if exists('/dev'):
            L = []
            L.extend(filter(lambda x: '.' in x, glob.glob('/dev/*usbmodem*')))
            L.extend(glob.glob('/dev/*usbserial*'))
            L.extend(glob.glob('/dev/ttyUSB*'))             # mac, or pi with adapter
            L.extend(glob.glob('/dev/ttyS0'))               # the horror

    if hint in L:
        L.remove(hint)
        L.append(hint)
    return L

def save_default_port(port):
    fn = join(dirname(__file__), 'saw.tmp')
    if exists(fn):
        config = json.load(open(fn))
    else:
        config = {}
    config['serialport'] = port
    json.dump(config, open(fn, 'w'))

def get_most_recent_id():
    try:
        fn = join(dirname(__file__), 'saw.tmp')
        return json.load(open(fn)).get('most_recent_id', None)
    except:
        pass
    return None

def save_most_recent_id(logger_id):
    fn = join(dirname(__file__), 'saw.tmp')
    if exists(fn):
        config = json.load(open(fn))
    else:
        config = {}

    config['most_recent_id'] = logger_id
    json.dump(config, open(fn, 'w'))


if '__main__' == __name__:
    
    import logging

