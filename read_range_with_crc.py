# Read the logger's memory into a binary file. Stops when empty page is reached.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import time, logging, sys, json, string
from os.path import exists
from serial import Serial
from crc_check import check_response


SPI_FLASH_SIZE_BYTE = 16*1024*1024
SPI_FLASH_PAGE_SIZE_BYTE = 256

logging.basicConfig(level=logging.DEBUG)

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
        logging.debug(cmd.strip())
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

        stop_logging_time = None

        validresponse = False
        for i in range(10):
            ser.write(b'is_logging')
            r = ser.read(size=1).decode().strip()
            #print(r)
            if r in ['0', '1']:
                validresponse = True
                break
            time.sleep(0.37)    # serial has low priority when logger is logging. gotta retry.
            print('(Retrying...)')
        if not validresponse:
            print('Invalid/no response from logger. Terminating.')
            sys.exit()
            
        if '1' == r:
            r = input('Logger is still logging. Stop logging? (yes/no; default=no)')
            if r.strip().lower() == 'yes':
                stopped = False
                for i in range(10):
                    ser.write(b'stop_logging')
                    ser.flushOutput()
                    r = ser.readline()  # not expecting anything, but still.
                    #r = ser.readline()  # expected response: 'Logging stopped.\n'
                    #print(r)
                    
                    ser.write(b'is_logging')
                    ser.flushOutput()
                    r = ser.read(size=1).decode().strip()
                    #print(r)
                    if '0' == r:
                        stopped = True
                        break
                if not stopped:
                    print('Logger not responding to stop_logging. Terminating.')
                    sys.exit()

                stop_logging_time = time.time()
            else:
                print('No change made. Terminating.')
                sys.exit()

        validresponse = False
        for i in range(10):
            ser.write(b'spi_flash_get_unique_id')
            flash_id = ser.readline().decode().strip()
            if 16 == len(flash_id) and flash_id.startswith('E') and all([c in string.hexdigits for c in flash_id]): # !
                validresponse = True
                break
            time.sleep(0.37)
            
        if not validresponse:
            print('Cannot read logger ID. Terminating.')
            sys.exit()

        print('Memory ID: {}'.format(flash_id))

        if stop_logging_time is not None:
            #store to kiwi_config...
            configfilename = 'kiwi_config_{}.txt'.format(flash_id)
            if exists(configfilename):
                config = json.loads(open(configfilename).read())
            else:
                # in case the config file doesn't exist (could have been (re)moved by the user)
                print('WARNING: config file not found.')
                config = {}
            config['stop_logging_time'] = stop_logging_time
            config = json.dumps(config, separators=(',', ':'))
            open('kiwi_config_{}.txt'.format(flash_id), 'w').write(config)

        fn = 'flash_dump_{}.bin'.format(flash_id)
        if exists(fn):
            r = input(fn + ' already exists. Overwrite? (yes/no; default=no)')
            if r.strip().lower() != 'yes':
                print('No change made. Terminating.')
                sys.exit()

        starttime = time.time()
        with open(fn, 'wb') as fout:
            for begin, end in split_range(BEGIN, END, STRIDE):
                line = read_range_core(begin, end)
                if len(line) <= 0:
                    raise RuntimeError('wut?')
                if STOP_ON_EMPTY and all([0xFF == b for b in line]):
# is this right? should I stop here?
                    print('Reached empty section in memory. Terminating.')
                    break
                fout.write(line)
        endtime = time.time()

    print('Output file: {}'.format(fn))
    print('Took {:.1f} minutes.'.format((endtime - starttime)/60))
    print('Done.')
