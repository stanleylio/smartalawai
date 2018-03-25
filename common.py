import logging


class InvalidResponseException(Exception):
    pass


def is_logging(ser, maxretry=10):
    logging.debug('is_logging()')

    ser.flushInput()

    logging.debug('Trying to determine if logger is currently logging...')    
    for i in range(maxretry):
        logging.debug('Retrying...')
        ser.write(b'is_logging')
        ser.flushOutput()
        r = ser.readline().decode().strip()
        logging.debug(r)
        if r in ['0', '1']:
            return '1' == r

    logging.warning('invalid/no response from logger')
    raise InvalidResponseException()


def stop_logging(ser, maxretry=10):
    logging.debug('stop_logging()')

    logging.debug('Trying to stop logging...')
    stopped = False
    for i in range(maxretry):
        logging.debug('Retrying...')
        ser.write(b'stop_logging')
        ser.flushOutput()

        try:
            if not is_logging(ser, maxretry=2):
                stopped = True
                break
        except InvalidResponseException:
            pass

    return stopped


if '__main__' == __name__:
    import logging
    from serial import Serial

    logging.basicConfig(level=logging.DEBUG)

    with Serial('COM18', 115200, timeout=1) as ser:
        print(is_logging(ser))
    
