# Plot a CSV file given a logger's unique ID.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import struct, math, sys, csv, logging, json, statistics
from os.path import join, exists
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from bin2csv import find
from common import ts2dt, dt2ts, get_most_recent_id

def get_config(fn):
    configfilename = fn.split('.')[0] + '.config'
    if not exists(configfilename):
        logging.error('Can\'t find config file for {}'.format(fn))
        return None
    logging.debug('Found config file {}'.format(configfilename))
    return json.load(open(configfilename))

def read_and_parse_data(fn):
    # Cory wants a human time column
    line = open(fn).readline().split(',')
    has_human_time = 10 == len(line) or 4 == len(line)

    D = []
    for line in open(fn):
        try:        # ignore parse error, effectively skipping header, if any
            if has_human_time:
                D.append([float(x) for x in line.split(',')[1:]])   # ignore the first column
            else:
                D.append([float(x) for x in line.split(',')])
        except ValueError:
            pass
    return zip(*D)


if '__main__' == __name__:

    logging.basicConfig(level=logging.WARNING)

    #fn = UNIQUE_ID + '.csv'
    #fn = input('Path to the CSV file: ').strip()

    default = 'last'
    tmp = get_most_recent_id()
    if tmp is not None and exists(join('data', tmp)):
        default = join('data/', tmp)

    d = find('data/*', dironly=True, default=default)
    fn = find(join(d, '*.csv'), fileonly=True, default='last')
    if fn is None:
        print('No CSV file found. Have you run bin2csv.py? Terminating.')
        sys.exit()

    config = get_config(fn)
    logger_name = config['name']

    if config.get('use_light', True):
        ts, t,p, als,white, r,g,b,w = read_and_parse_data(fn)
    else:
        ts, t,p = read_and_parse_data(fn)
    begin, end = ts2dt(min(ts)), ts2dt(max(ts))

    if len(ts) <= 1:
        print('Only less than two measurements are available. ABORT.')

    print('{:,} samples from {} to {} spanning {}, interval {:.3}s'.format(
        len(ts),
        begin,
        end,
        end - begin,
        ts[1] - ts[0]))

    dt = [ts2dt(tmp) for tmp in ts]

    print('Plotting time series...')
    fig, ax = plt.subplots(4 if config['use_light'] else 2, 1, figsize=(16, 9), sharex=True)

    [plt.setp(a.get_xticklabels(), visible=False) for a in ax[:-1]]
    ax[-1].set_xlabel('UTC Time')
    ax[-1].xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))

    if logger_name is not None:
        logger_name = logger_name.strip()
        if len(logger_name):
            fig.suptitle(fn + ' ("{}")'.format(logger_name))
    else:
        fig.suptitle(fn)

    ax[0].plot_date(dt, t, 'r.:', label='℃')
    ax[1].plot_date(dt, p, '.:', label='kPa')

    if config.get('use_light', True):
        ax[2].plot_date(dt, als, '.:', label='HDR_ALS', alpha=0.5)
        ax[2].plot_date(dt, white, '.:', label='HDR_W', alpha=0.5)

        ax[3].plot_date(dt, r, 'r.:', label='R', alpha=0.5)
        ax[3].plot_date(dt, g, 'g.:', label='G', alpha=0.5)
        ax[3].plot_date(dt, b, 'b.:', label='B', alpha=0.5)
        ax[3].plot_date(dt, w, 'k.:', label='W', alpha=0.2)

    [a.legend(loc=2) for a in ax]
    [a.grid(True) for a in ax]

    plt.tight_layout()
    plt.gcf().autofmt_xdate()

    print('Saving plot to disk...')
    plt.savefig(fn.split('.')[0] + '.png', dpi=300)
    plt.show()
