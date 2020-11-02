import logging, sys, struct, math
from serial import Serial
from kiwi import Kiwi
from datetime import datetime
from common import ts2dt, dt2ts
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


def birdseye_read(kiwi, downsample_N):
    config = kiwi.get_config(use_cached=True)
    sample_count = kiwi.get_sample_count()
    number_to_read = min(downsample_N, sample_count)
    STRIDE = int(sample_count//number_to_read)
    m = '{:,} in steps of {:,}'.format(number_to_read, STRIDE) if STRIDE > 1 else 'everything'
    print(' {:,} sample{} in memory.'.format(sample_count, 's' if sample_count > 1 else ''))
    print('Requested {:,} sample{}; will read {}.'.format(downsample_N, 's' if downsample_N > 1 else '', m))
    print('First sample taken at {} ({} UTC).'.format(ts2dt(config['start'], utc=False), ts2dt(config['start'], utc=True)))
    print('Sampling interval: {:.3f} second'.format(config['interval_ms']*1e-3))

    # - - -
    
    D = []
    current_page_index = None
    current_page = None
    sample_indices = list(range(0, sample_count, STRIDE))
    addr = [kiwi.sampleindex2flashaddress(i) for i in sample_indices]
    print('Reading', end='', flush=True)
    for sample_index, (page_i,byte_i) in zip(sample_indices, addr):
        #print(sample_index, page_i, byte_i)
        try:
            if 0 == (sample_index//STRIDE) % math.ceil(sample_count//STRIDE/10):
                print('.', end='', flush=True)

            if current_page_index != page_i:
                logging.debug('Reading logger...')
                begin = page_i*Kiwi.SPI_FLASH_PAGE_SIZE_BYTE
                end = (page_i+1)*Kiwi.SPI_FLASH_PAGE_SIZE_BYTE - 1
                current_page = kiwi.read_range_core(begin, end)
                if len(current_page) != end - begin + 1:
                    logging.warning('Invalid response length. Skipping sample {}'.format(sample_index))
                    continue
                current_page_index = page_i
            else:
                logging.debug('reuse')

            d = struct.unpack(kiwi.sample_struct_fmt, current_page[byte_i : byte_i + kiwi.SAMPLE_SIZE_BYTE])
            D.append([sample_index, *d])

        except KeyboardInterrupt:
            print(' User interrupted.')
            break

    return D, STRIDE

def birdseye_plot(D, STRIDE, config, sample_count, use_utc):
    D = list(zip(*D))
    D[0] = [ts2dt(i*config['interval_ms']*1e-3 + config['start'], utc=use_utc) for i in D[0]]

    print(' plotting... ', end='', flush=True)
    
    fig, ax = plt.subplots(4 if config['use_light'] else 2, 1, figsize=(16, 9), sharex=True)
    for tmp in ax[:-1]:
        plt.setp(tmp.get_xticklabels(), visible=False)
    ax[-1].set_xlabel('UTC Time' if use_utc else 'Local Time')

    if STRIDE > 1:
        ax[0].set_title('Memory Overview (plotting one out of every {:,})'.format(STRIDE, sample_count))
    else:
        ax[0].set_title('Memory Overview (plotting everything)')
        
    # add caption
    s = 'Logger "{}" (ID={})'.format(config['name'], config['id'])
    s += '\n{:,} samples from {} to {} spanning ~{:.1f} days'.format(sample_count,
                                                                   min(D[0]).isoformat()[:19].replace('T', ' '),
                                                                   max(D[0]).isoformat()[:19].replace('T', ' '),
                                                                   (max(D[0]) - min(D[0])).total_seconds()/3600/24)
    s += '\nSample interval={:.3f} second{}'.format(config['interval_ms']*1e-3, 's' if config['interval_ms'] > 1000 else '')

    if STRIDE > 1:
        s += '\n{:,} out of {:,} samples plotted (in steps of {:,})'.format(len(D[0]), sample_count, STRIDE)
    else:
        s += '\nAll samples plotted'
    
    plt.figtext(0.99, 0.01,
                s,
                horizontalalignment='right',
                color='k',
                alpha=0.5)

    ax[0].plot_date(D[0], D[1], 'r.:', label='℃')
    ax[0].legend(loc=2)
    ax[0].grid(True)

    ax[1].plot_date(D[0], D[2], '.:', label='kPa')
    ax[1].legend(loc=2)
    ax[1].grid(True)

    if config['use_light']:
        ax[2].plot_date(D[0], D[3], '.:', label='HDR_ALS', alpha=0.5)
        ax[2].plot_date(D[0], D[4], '.:', label='HDR_W', alpha=0.5)
        ax[2].legend(loc=2)
        ax[2].grid(True)

        ax[3].plot_date(D[0], D[5], 'r.:', label='R', alpha=0.5)
        ax[3].plot_date(D[0], D[6], 'g.:', label='G', alpha=0.5)
        ax[3].plot_date(D[0], D[7], 'b.:', label='B', alpha=0.5)
        ax[3].plot_date(D[0], D[8], 'k.:', label='W', alpha=0.2)
        ax[3].legend(loc=2)
        ax[3].grid(True)

    ax[-1].xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))
    plt.tight_layout()
    plt.gcf().autofmt_xdate()

    #print('Saving plot to disk...')
    #plt.savefig(fn.split('.')[0] + '.png', dpi=300)
    print('voila!')
    plt.show()


if '__main__' == __name__:

    logging.basicConfig(level=logging.WARNING)

    # Read this many samples from memory, evenly spaced.
    # If there aren't enough samples, read them all.
    DOWNSAMPLE_N = 128
    USE_UTC = False
    
    # - - -

    from common import serial_port_best_guess, save_default_port
    DEFAULT_PORT = serial_port_best_guess(prompt=True)
    PORT = input('PORT=? (default={}):'.format(DEFAULT_PORT)).strip()
    # empty input, use default
    if '' == PORT:
        PORT = DEFAULT_PORT

    with Serial(PORT, 115200, timeout=1) as ser:
        kiwi = Kiwi(ser)

        if kiwi.is_logging():
            r = input('Logger is running. Stop it? (yes/no; default=no)')
            if r.strip().lower() in ['yes']:
                logging.debug('User wants to stop logging.')
                kiwi.stop_logging()
            else:
                print('Cannot proceed while logger is still running. Terminating.')
                sys.exit()
    
        config = kiwi.get_config()
        print('Found logger "{}" (ID={})'.format(config['name'], config['id']))
        print('Battery voltage {:.1f} V'.format(kiwi.get_battery_voltage()))

        print('Scanning logger memory...', end='', flush=True)
        sample_count = kiwi.get_sample_count()
        if 0 == sample_count:
            print(' Logger is empty. Terminating.')
            sys.exit()

        D,STRIDE = birdseye_read(kiwi, DOWNSAMPLE_N)

    # - - -
    # Done with talking to the logger. Now plotting...

    birdseye_plot(D, STRIDE, config, USE_UTC)
