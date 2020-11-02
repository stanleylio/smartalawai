# Extract data from logger into a CSV and a binary file.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import time, logging, sys, json
from os import makedirs
from os.path import join, exists
from serial import Serial
from serial.serialutil import SerialException
from kiwi import Kiwi
from common import save_most_recent_id
from bin2csv import bin2csv
from datetime import timedelta


# Read memory range (in byte) from here...
BEGIN = 0
# ... to here
END = Kiwi.SPI_FLASH_SIZE_BYTE - 1
# Request this many bytes per call
# The response will be 4-byte longer than requested due to the CRC32 at the
# end, but that's checked and striped by kiwi.read_range_core().
CHUNK_SIZE = 32*Kiwi.SPI_FLASH_PAGE_SIZE_BYTE
# Stop reading if the response is all empty (0xff for NOR flash)
STOP_ON_EMPTY = True


def split_range(begin, end, pkt_size):
    assert end >= begin
    A = tuple(range(begin, end, pkt_size))
    B = [x + pkt_size - 1 for x in A]
    return list(zip(A, B))

def read_memory(kiwi):

    config = kiwi.get_config(use_cached=True)

    print('Name: {}'.format(config['name']))
    print('ID: {}'.format(config['id']))
    print('Sample interval = {:.3f} second'.format(config['interval_ms']*1e-3))
    last_used_page = kiwi.find_last_used_page()
    used_page_count = last_used_page + 1 if last_used_page is not None else 0
    if 0 == used_page_count:
        print('Logger is empty. ABORT.')
        sys.exit()
    print('{:,} samples (~{:.0f}% full)'.format(kiwi.get_sample_count(),
                                              100*used_page_count/Kiwi.SPI_FLASH_PAGE_COUNT))

    tmp = kiwi.get_battery_voltage()
    if tmp < 1.1:
        r = input('Battery voltage is rather low ({:.1f} V). Proceed regardless? (yes/no; default=yes)'.format(tmp))
        if r.strip().lower() in ['no', 'n']:
            print('No change made. ABORT.')
            sys.exit()

    makedirs(join('data', config['id']), exist_ok=True)

    configfilename = join('data', config['id'], '{}_{}.config'.format(config['id'], config['start']))
    # preserve config data in file if it exists (created when logging started)
    if exists(configfilename):
        tmp = json.loads(open(configfilename).read())
        tmp.update(config)
        config = tmp
    open(configfilename, 'w').write(json.dumps(config, separators=(',', ':')))

    fn_bin = join('data', config['id'], '{}_{}.bin'.format(config['id'], config['start']))
    if exists(fn_bin):
        r = input(fn_bin + ' already exists. Overwrite? (yes/no; default=no)')
        if r.strip().lower() != 'yes':
            print('ABORT.')
            sys.exit()

    starttime = time.time()
    should_continue = True
    with open(fn_bin, 'wb') as fout:
        for begin, end in split_range(BEGIN, END, CHUNK_SIZE):
            #print('Reading {:X} to {:X} ({:.2f}%; {:.2f}% of total capacity; time elapse: {})'.\
            print('Reading {:X} to {:X} (~{:.2f}%; time elapse: {})'.\
                  format(begin,
                         end,
                         100*(end//Kiwi.SPI_FLASH_PAGE_SIZE_BYTE)/Kiwi.SPI_FLASH_PAGE_COUNT,
                         #end/Kiwi.SPI_FLASH_SIZE_BYTE*100,
                         timedelta(seconds=time.time() - starttime)))
            for _ in range(16):
                try:
                    line = kiwi.read_range_core(begin, end)
                    if line is not None:
                        break
                except KeyboardInterrupt:
                    print('User interrupted.')
                    should_continue = False
                    break
                except:
                    logging.warning('read_range_core() failed')

            if not should_continue:
                break

            if line is None:
                print('Error reading logger memory. Stopped reading.')
                break
                
            if STOP_ON_EMPTY and all([0xFF == b for b in line]):
                print('Reached empty section in memory.')
                break
            fout.write(line)
    endtime = time.time()
    print('Took {:.1f} minutes.'.format((endtime - starttime)/60))
    return fn_bin


if '__main__' == __name__:

    logging.basicConfig(level=logging.WARNING)

    # find the serial port to use from user, from history, or make a guess
    # if on Windows, print the list of COM ports
    from common import serial_port_best_guess, save_default_port
    
    DEFAULT_PORT = serial_port_best_guess(prompt=True)
    PORT = input('PORT=? (default={}):'.format(DEFAULT_PORT)).strip()
    # empty input, use default
    if '' == PORT:
        PORT = DEFAULT_PORT

    with Serial(PORT, 115200, timeout=2) as ser:

        save_default_port(PORT)

        kiwi = Kiwi(ser)

        if kiwi.is_logging():
            r = input('Logger is still logging. Stop logging? (yes/no; default=no)')
            if r.strip().lower() == 'yes':
                kiwi.stop_logging()
                if kiwi.is_logging():
                    print('Could not stop logger. ABORT.')
                    sys.exit()
            else:
                print('No change made. ABORT.')
                sys.exit()

        config = kiwi.get_config(use_cached=True)
        fn_bin = read_memory(kiwi)

    # - - - - -
    fn_csv = fn_bin.rsplit('.')[0] + '.csv'
    bin2csv(fn_bin, fn_csv, config)
    save_most_recent_id(config['id'])
    
    print('Output CSV file: {}'.format(fn_csv))
    print('Output binary file: {}'.format(fn_bin))
    print('Save/copy this, you will need it if you want to run plot_csv.py: {}'.format(config['id']))
