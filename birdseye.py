# Print metadata of attached logger.
#
# MESH Lab
# University of Hawaii
# Copyright 2019 Stanley H.I. Lio
# hlio@hawaii.edu
import time, logging, sys, struct
from serial import Serial
from common import get_logger_name, get_flash_id, read_vbatt, is_logging, get_logging_config,\
     find_last_used_page, read_page,\
     SPI_FLASH_SIZE_BYTE, SPI_FLASH_PAGE_SIZE_BYTE, SAMPLE_SIZE_BYTE, SAMPLE_INTERVAL_CODE_MAP,\
     InvalidResponseException
from dev.set_rtc import read_rtc, ts2dt
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


tags = ['UTC_datetime', 'T_DegC', 'P_kPa', 'ambient_light_hdr', 'white_light_hdr', 'red', 'green', 'blue', 'white']
SAMPLE_PER_PAGE = SPI_FLASH_PAGE_SIZE_BYTE//SAMPLE_SIZE_BYTE


# given a sample index, calculate the page address and the byte index within that page
def sampleindex2flashaddress(sample_index):
    return int(sample_index//SAMPLE_PER_PAGE), int((sample_index%SAMPLE_PER_PAGE)*SAMPLE_SIZE_BYTE)

# given a sample index, time of the first sample, and the sample interval, calculate the sample index
def date2sampleindex(t, logging_start_time, sample_interval_second):
    ts = dt2ts(t) if type(t) is datetime else t
    return (t - logging_start_time)//sample_interval_second
    

if '__main__' == __name__:
    
    # Read this many samples from memory, evenly spaced.
    # If there aren't enough samples, read them all.
    DOWNSAMPLE_N = 512
    USE_UTC = False

    # - - -
    
    logging.basicConfig(level=logging.WARNING)

    # find the serial port to use from user, from history, or make a guess
    # if on Windows, print the list of COM ports
    from common import serial_port_best_guess, save_default_port
    print('Detected ports:')
    DEFAULT_PORT = serial_port_best_guess(prompt=True)
    print('- - -')
    PORT = input('PORT=? (default={})'.format(DEFAULT_PORT)).strip()
    # empty input, use default
    if '' == PORT:
        PORT = DEFAULT_PORT


    with Serial(PORT, 115200, timeout=1) as ser:

        save_default_port(PORT)

        if is_logging(ser):
            r = input('Logger is logging. Stop it? (yes/no; default=no)')
            if r.strip().lower() in ['yes']:
                logging.debug('User wants to stop logging.')
                ser.write(b'stop_logging')
            else:
                print('This script cannot proceed while logger is still running. Abort.')
                sys.exit()

        logger_name = get_logger_name(ser)
        flash_id = get_flash_id(ser)
        vbatt = read_vbatt(ser)
        rtc = read_rtc(ser)
        config = get_logging_config(ser)
        logging_start_time = config['logging_start_time']
        sample_interval_second = SAMPLE_INTERVAL_CODE_MAP[config['logging_interval_code']]

        print('Logger "{}" (ID={})'.format(logger_name, flash_id))
        print('Battery voltage {:.1f} V, clock {}'.format(vbatt, ts2dt(rtc)))
        print('Scanning logger memory...')
        page_used = find_last_used_page(ser)
        page_used = 0 if page_used is None else page_used + 1
        
        #print('{} page(s) in use.'.format(page_used))
        sample_count = page_used * SAMPLE_PER_PAGE
        if 0 == sample_count:
            print('Logger is empty. Terminating.')
            sys.exit()

        number_to_read = min(DOWNSAMPLE_N, sample_count)
        STRIDE = int(sample_count // number_to_read)
        m = '{} in steps of {}'.format(number_to_read, STRIDE) if STRIDE > 1 else 'everything'
        print('{} sample(s) in memory ({} page(s) out of {}). Requested {} sample(s); will read {}.'.\
              format(sample_count, page_used, SPI_FLASH_SIZE_BYTE//SPI_FLASH_PAGE_SIZE_BYTE, DOWNSAMPLE_N, m))
        print('First sample taken at {}.'.format(ts2dt(logging_start_time)))
        
        # - - -

        assert (0,0) == sampleindex2flashaddress(date2sampleindex(logging_start_time, logging_start_time, sample_interval_second))

        ser.flushInput()
        ser.flushOutput()
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        D = []
        current_page_index = None
        current_page = None
        for sample_index in range(0, sample_count, STRIDE):
            try:
                page, index = sampleindex2flashaddress(sample_index)
                if current_page_index != page:
                    logging.debug('Reading logger...')
                    current_page = read_page(ser, page)
                    current_page_index = page

                d = struct.unpack('ffHHHHHH', current_page[index : index + SAMPLE_SIZE_BYTE])
                D.append([sample_index, *d])
            except KeyboardInterrupt:
                print('Use interrupted. Proceed to plot.')
                break

        D = list(zip(*D))
        assert len(D) == len(tags)
        D[0] = [ts2dt(i*sample_interval_second + logging_start_time) for i in D[0]]

        # - - -

        print('Plotting... ', end='')
        
        fig, ax = plt.subplots(4, 1, figsize=(16, 9), sharex=True)
        for tmp in ax[:-1]:
            plt.setp(tmp.get_xticklabels(), visible=False)
        ax[-1].set_xlabel('UTC Time')

        if STRIDE > 1:
            plt.suptitle('Memory Overview (plotting one out of every {:,})'.format(STRIDE, sample_count))
        else:
            plt.suptitle('Memory Overview (plotting everything)')
            
        ax[0].plot_date(D[0], D[1], 'r.:', label='Deg.C')
        ax[0].legend(loc=2)
        ax[0].grid(True)

        ax[1].plot_date(D[0], D[2], '.:', label='kPa')
        ax[1].legend(loc=2)
        ax[1].grid(True)

        ax[2].plot_date(D[0], D[3], '.:', label='als', alpha=0.5)
        ax[2].plot_date(D[0], D[4], '.:', label='white', alpha=0.5)
        ax[2].legend(loc=2)
        ax[2].grid(True)

        ax[3].plot_date(D[0], D[5], 'r.:', label='r', alpha=0.5)
        ax[3].plot_date(D[0], D[6], 'g.:', label='g', alpha=0.5)
        ax[3].plot_date(D[0], D[7], 'b.:', label='b', alpha=0.5)
        ax[3].plot_date(D[0], D[8], 'k.:', label='w', alpha=0.2)
        ax[3].legend(loc=2)
        ax[3].grid(True)

        ax[-1].xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))
        plt.tight_layout()
        plt.gcf().autofmt_xdate()

        #print('Saving plot to disk...')
        #plt.savefig(fn.split('.')[0] + '.png', dpi=300)
        print('voila!')
        plt.show()