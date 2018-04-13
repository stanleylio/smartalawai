# Plot a CSV file given a logger's unique ID.
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import struct, math, sys, csv, logging, json
from os.path import join, exists
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np
from scipy.stats import describe
from bin2csv import find
from common import ts2dt, dt2ts


logging.basicConfig(level=logging.WARNING)


SAMPLE_SIZE = 20    # size of one sample in bytes
PAGE_SIZE = 256

# - - -


#fn = UNIQUE_ID + '.csv'
#fn = input('Path to the CSV file: ').strip()

d = find('data/*', dironly=True)
fn = find(join(d, '*.csv'), fileonly=True)
if fn is None:
    print('No CSV file found. Have you run bin2csv.py? Terminating.')
    sys.exit()

# find the name of the logger, if possible
logger_name = None
configfilename = fn.split('.')[0] + '.config'
if exists(configfilename):
    logging.debug('Found config file {}'.format(configfilename))
    config = json.load(open(configfilename))
    logger_name = config.get('logger_name', None)


#D = []
#for line in csv.reader(open(fn, newline='')):
#    D.append([float(x) for x in line])
D = [[float(x) for x in line] for line in csv.reader(open(fn, newline=''))]

ts, t,p, als,white, r,g,b,w = zip(*D)
begin, end = ts2dt(min(ts)), ts2dt(max(ts))
print('{} samples from {} to {} spanning {}, average interval {:.3}s'.format(
    len(D),
    begin,
    end,
    end - begin,
    np.mean(np.diff(ts))))

# - - -

#print(describe(p))

# also PSD... TODO

print('Calculating Temperature statistics...')
plt.figure(figsize=(16, 9))

ax = plt.subplot(211)
ax.hist(np.diff(t), color='r', bins='auto')
if logger_name is not None:
    logger_name = logger_name.strip()
    if len(logger_name):
        ax.set_title('Step Size Distribution (Temperature; "{}")'.format(logger_name))
else:
    ax.set_title('Step Size Distribution (Temperature)')
ax.set_xlabel('Deg.C')
ax.set_ylabel('(count)')
ax.grid(True)

print('Calculating Pressure statistics...')
ax = plt.subplot(212)
ax.hist(np.diff(p), bins='auto')
if logger_name is not None:
    logger_name = logger_name.strip()
    if len(logger_name):
        ax.set_title('Step Size Distribution (Pressure; "{}")'.format(logger_name))
else:
    ax.set_title('Step Size Distribution (Pressure)')
ax.set_xlabel('kPa')
ax.set_ylabel('(count)')
ax.grid(True)

plt.tight_layout()

#plt.show()
#sys.exit()


'''fig = plt.figure()
ax = plt.subplot()
tmp = np.diff(p)
print('{} unique step sizes'.format(len(np.unique(tmp))))
#ax.scatter(np.arange(0, len(tmp)), sorted(np.abs(tmp)))
ax.scatter(np.arange(0, len(tmp)), sorted(tmp))
ax.set_title('Step sizes (sorted)')
ax.set_ylabel('kPa')
ax.grid(True)'''

#plt.show()
#sys.exit()


#print('Step sizes: ', end='')
#print(sorted(np.unique(tmp)))

dt = [ts2dt(tmp) for tmp in ts]

print('Plotting time series...')
plt.figure(figsize=(16, 9))

ax1 = plt.subplot(411)
if logger_name is not None:
    logger_name = logger_name.strip()
    if len(logger_name):
        ax1.set_title(fn + ' ("{}")'.format(logger_name))
else:
    ax1.set_title(fn)

ax1.plot_date(dt, t, 'r.:', label='Deg.C')
plt.setp(ax1.get_xticklabels(), visible=False)
plt.legend(loc=2)
plt.grid(True)

ax2 = plt.subplot(412, sharex=ax1)
ax2.plot_date(dt, p, '.:', label='kPa')
plt.setp(ax2.get_xticklabels(), visible=False)
plt.legend(loc=2)
plt.grid(True)

ax3 = plt.subplot(413, sharex=ax1)
plt.plot_date(dt, als, '.:', label='als', alpha=0.5)
plt.plot_date(dt, white, '.:', label='white', alpha=0.5)
plt.setp(ax3.get_xticklabels(), visible=False)
plt.legend(loc=2)
plt.grid(True)

plt.subplot(414, sharex=ax1)
plt.plot_date(dt, r, 'r.:', label='r', alpha=0.5)
plt.plot_date(dt, g, 'g.:', label='g', alpha=0.5)
plt.plot_date(dt, b, 'b.:', label='b', alpha=0.5)
plt.plot_date(dt, w, 'k.:', label='w', alpha=0.2)
plt.legend(loc=2)
plt.grid(True)

plt.xlabel('UTC Time')

plt.tight_layout()
plt.gcf().autofmt_xdate()
ax1.xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))

print('Saving plot to disk...')
plt.savefig(fn.split('.')[0] + '.png', dpi=300)
plt.show()

print('Done.')
