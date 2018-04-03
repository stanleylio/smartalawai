# Read the logger's memory into a binary file. Stops when empty page is reached.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import time, logging, sys, json
from os.path import exists
from serial import Serial
from crc_check import check_response
from common import is_logging, stop_logging, get_logging_config, read_vbatt, get_logger_name, get_flash_id, InvalidResponseException, SAMPLE_INTERVAL_CODE_MAP


SPI_FLASH_SIZE_BYTE = 16*1024*1024
SPI_FLASH_PAGE_SIZE_BYTE = 256


logging.basicConfig(level=logging.WARNING)


# read memory range from here
BEGIN = 0
# to here
END = SPI_FLASH_SIZE_BYTE - 1
# request this many bytes each time (there's CRC32 at the end of each transaction)
STRIDE = 16*SPI_FLASH_PAGE_SIZE_BYTE
# retry at most this many times on comm error
MAX_RETRY = 10
# stop reading if latest response is all empty (0xFF for NOR flash)
STOP_ON_EMPTY = True


def read_range_core(begin, end):
    assert end >= begin

    cmd = 'spi_flash_read_range{:x},{:x}\n'.format(begin, end)

    for retry in range(MAX_RETRY):
        ser.flushInput()
        ser.flushOutput()
        #logging.debug(cmd.strip())
        #logging.debug('Reading {:X} to {:X} ({:.2f}%)'.format(begin, end, end/SPI_FLASH_SIZE_BYTE*100))
        ser.write(cmd.encode())
        expected_length = end - begin + 1 + 4
        line = ser.read(expected_length)
        if len(line) != expected_length:
            time.sleep(0.1)
            logging.warning('Response length mismatch. Expected {} bytes, got {} bytes'.format(expected_length, len(line)))
            continue
        if not check_response(line):
            time.sleep(0.1)
            logging.warning('CRC failure')
            continue
        return line[:-4]    # strip CRC32
    return bytearray()


def split_range(begin, end, pkt_size):
    assert end >= begin
    pairs = []
    currentaddr = begin
    while currentaddr <= end:
        stride = min(end - currentaddr + 1, pkt_size)
        pairs.append([currentaddr, currentaddr + stride - 1])
        currentaddr += stride
    return pairs


if '__main__' == __name__:

    DEFAULT_PORT = 'COM18'
    PORT = input('PORT=? (default={})'.format(DEFAULT_PORT))
    if '' == PORT:
        PORT = DEFAULT_PORT

    with Serial(PORT, 115200, timeout=2) as ser:

        ser.write(b'\n\n\n')
        ser.flushOutput()
        ser.flushInput()

        stop_logging_time = None

        if is_logging(ser):
            r = input('Logger is still logging. Stop logging? (yes/no; default=no)')
            if r.strip().lower() == 'yes':
                if not stop_logging(ser):
                    print('Could not stop logger. Terminating.')
                    sys.exit()

                stop_logging_time = time.time()
            else:
                print('No change made. Terminating.')
                sys.exit()

        try:
            name = get_logger_name(ser)
            print('Name: {}'.format(name))
            flash_id = get_flash_id(ser)
            print('ID: {}'.format(flash_id))
        except InvalidResponseException:
            print('Cannot read logger name/ID. Terminating.')
            sys.exit()

        metadata = get_logging_config(ser)
        logging.debug(metadata)

        #store meta data to config file
        configfilename = '{}.config'.format(flash_id)
        if exists(configfilename):
            config = json.loads(open(configfilename).read())
        else:
            # in case the config file doesn't exist (could have been (re)moved by the user)
            print('WARNING: config file not found.')
            config = {}
        config['logging_start_time'] = metadata['logging_start_time']
        config['logging_stop_time'] = metadata['logging_stop_time']
        config['logging_interval_code'] = metadata['logging_interval_code']
        if stop_logging_time is not None:
            config['stop_logging_time'] = stop_logging_time
        else:
            if 'stop_logging_time' in config:
                del config['stop_logging_time']     # remove old record if any
        config['vbatt_post'] = read_vbatt(ser)
        logging.debug(config)
        open(configfilename, 'w').write(json.dumps(config, separators=(',', ':')))

        print('Sample interval = {} second'.format(SAMPLE_INTERVAL_CODE_MAP[config['logging_interval_code']]))

        fn = '{}.bin'.format(flash_id)
        if exists(fn):
            r = input(fn + ' already exists. Overwrite? (yes/no; default=no)')
            if r.strip().lower() != 'yes':
                print('No change made. Terminating.')
                sys.exit()

        starttime = time.time()
        with open(fn, 'wb') as fout:
            for begin, end in split_range(BEGIN, END, STRIDE):
                print('Reading {:X} to {:X} ({:.2f}%)'.format(begin, end, end/SPI_FLASH_SIZE_BYTE*100))
                line = read_range_core(begin, end)
                if len(line) <= 0:
                    raise RuntimeError('wut?')
                if STOP_ON_EMPTY and all([0xFF == b for b in line]):
                    print('Reached empty section in memory. Terminating.')
                    break
                fout.write(line)
        endtime = time.time()

    print('Output file: {}'.format(fn))
    input('Took {:.1f} minutes. Press RETURN to exit.'.format((endtime - starttime)/60))
