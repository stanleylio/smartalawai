# Plot a CSV file given a logger's unique ID.
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import struct, math, sys, csv, calendar
from datetime import datetime
from os.path import join
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import numpy as np
from scipy.stats import describe



SAMPLE_SIZE = 20    # size of one sample in bytes
PAGE_SIZE = 256

# - - -

def dt2ts(dt=None):
    if dt is None:
        dt = datetime.utcnow()
    return calendar.timegm(dt.timetuple()) + (dt.microsecond)*(1e-6)

def ts2dt(ts=None):
    if ts is None:
        ts = dt2ts()
    return datetime.utcfromtimestamp(ts)


#fn = UNIQUE_ID + '.csv'
#fn = input('Path to the CSV file: ').strip()
from bin2csv import find

d = find('data/*')
fn = find(join(d, '*.csv'))


#D = []
#for line in csv.reader(open(fn, newline='')):
#    D.append([float(x) for x in line])
D = [[float(x) for x in line] for line in csv.reader(open(fn, newline=''))]

print('{} samples'.format(len(D)))
ts, t,p, als,white, r,g,b,w = zip(*D)
print('From {} to {}'.format(ts2dt(min(ts)), ts2dt(max(ts))))

# - - -

print(describe(p))

# also PSD... TODO

fig, ax = plt.subplots()
tmp = np.diff(p)
ax.hist(tmp, bins='auto')
ax.set_title('Distribution of Step Sizes - np.diff()')
ax.set_ylabel('(count)')
ax.grid(True)

fig, ax = plt.subplots()
tmp = np.diff(p)
print('{} unique step sizes'.format(len(np.unique(tmp))))
#ax.scatter(np.arange(0, len(tmp)), sorted(np.abs(tmp)))
ax.scatter(np.arange(0, len(tmp)), sorted(tmp))
ax.set_title('Step sizes (sorted)')
ax.set_ylabel('kPa')
ax.grid(True)

#plt.show()
#sys.exit()


#print('Step sizes: ', end='')
#print(sorted(np.unique(tmp)))

dt = [ts2dt(tmp) for tmp in ts]

plt.figure(figsize=(16, 9))

ax1 = plt.subplot(411)
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

plt.gcf().autofmt_xdate()
ax1.xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))

plt.savefig(fn.split('.')[0] + '.png', dpi=600)
plt.show()
