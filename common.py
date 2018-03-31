#
# logging_start_time: logger's RTC time when logging started
# logging_stop_time: logger's RTC time when logging stopped
# logging_interval_code: internal value corresponding to sampling interval
# start_logging_time: user's computer time when logging started
# stop_logging_time: user's computer time if and when logging stopped by user (while logger was still running)
# flash_id
#
import logging, random, time, string


SAMPLE_INTERVAL_CODE_MAP = {0:1/5, 1:1, 2:60}


class InvalidResponseException(Exception):
    pass


def is_logging(ser, maxretry=10):
    ser.flushOutput()
    ser.flushInput()

    for i in range(maxretry):
        try:
            if i > 0:
                logging.debug('is_logging(): retrying...')
            ser.write(b'\n')
            ser.write(b'is_logging')
            ser.flushOutput()
            r = ser.readline().decode().strip()
            logging.debug('is_logging(): ' + r)
            return '1' == r[0]
        except IndexError:
            pass
        time.sleep(random.randint(0, 90)/100)

    raise InvalidResponseException('Invalid/no response from logger: ' + r)


def stop_logging(ser, maxretry=10):
    logging.debug('stop_logging()')
    ser.flushOutput()
    ser.flushInput()

    stopped = False
    for i in range(maxretry):
        if i > 0:
            logging.debug('stop_logging(): retrying...')
        ser.write(b'stop_logging')
        ser.flushOutput()

        if not is_logging(ser):
            stopped = True
            break

    return stopped


def probably_empty(ser, maxretry=5):
    ser.write(b'is_logging')
    r = ser.readline().decode().strip().split(',')
    if not ('0' == r[1]) and ('0' == r[2]):
        logging.debug('probably_empty(): memory indices not clean')
        return False
    
    for i in range(maxretry):
        ser.write(b'spi_flash_read_range0,ff\n')
        r = ser.readline()
        if 256+4 == len(r):
            if all([0xFF == rr for rr in r[:-4]]):
                ser.flushInput()
                return True
            else:
                ser.flushInput()
                return False
        else:
            continue
    ser.flushInput()
    return False


def get_logging_config(ser, maxretry=10):
    tags = ['logging_start_time', 'logging_stop_time', 'logging_interval_code', 'current_page_addr', 'byte_index_within_page']
    
    for i in range(maxretry):
        ser.write(b'get_logging_config')
        try:
            line = ser.readline().decode().strip().split(',')
            if len(line) >= 3:  # ... isn't there any simple self-descriptive format? or an ultra-intelligent parser?
                return dict(zip(tags, [int(tmp) for tmp in line]))
        except:
            pass
    raise InvalidResponseException('Invalid/no response from logger: ' + r)


def read_vbatt(ser, maxretry=10):
    for i in range(maxretry):
        try:
            ser.write(b'read_sys_volt')
            r = ser.readline().decode().strip().split(',')
            return round(float(r[1]), 2)
        except ValueError:
            pass
    raise InvalidResponseException('Invalid/no response from logger: ' + r)


def get_flash_id(ser, maxretry=10):
    logging.debug('get_flash_id()')
    ser.flushOutput()
    ser.flushInput()

    for i in range(maxretry):
        ser.write(b'spi_flash_get_unique_id')
        flash_id = ser.readline().decode().strip()
        if 16 == len(flash_id) and flash_id.startswith('E') and all([c in string.hexdigits for c in flash_id]): # !
            return flash_id
        time.sleep(random.randint(0, 50)/100)
    raise InvalidResponseException('Invalid/no response from logger: ' + r)


if '__main__' == __name__:
    import logging
    from serial import Serial

    logging.basicConfig(level=logging.DEBUG)

    with Serial('COM18', 115200, timeout=1) as ser:
        print(is_logging(ser))
        print(read_vbatt(ser))
        print(probably_empty(ser))
        print(get_logging_config(ser))
    
