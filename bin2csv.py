# Convert a flash dump (.bin) file to a CSV file.
# Timestamps are reconstructed from the config file "kiwi_config_[UNIQUE ID].txt"
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESH Lab
# University of Hawaii
import struct, math, sys, csv, json
from os.path import exists
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import describe


#UNIQUE_ID = 'E4675477971F1421'
UNIQUE_ID = input('ID=')


binfilename = 'flash_dump_' + UNIQUE_ID + '.bin'
configfilename = 'kiwi_config_' + UNIQUE_ID + '.txt'
outputfilename = UNIQUE_ID + '.csv'

assert exists(binfilename)
assert exists(configfilename)
#assert not exists(outputfilename)

SAMPLE_SIZE = 20    # size of one sample in bytes
PAGE_SIZE = 256
SAMPLE_INTERVAL_S = 1/5

# - - -

print('Reading binary file {}'.format(binfilename))
buf = bytearray()
with open(binfilename, 'rb') as fin:
    buf = fin.read()

#print(buf)
#print(len(buf))


print('Parsing...')
good = True
D = []
for page in range(len(buf)//PAGE_SIZE):
    if not good:
        break
    try:
#        print('Page address: 0x{:06X}'.format(page*PAGE_SIZE))
        for i in range(0, PAGE_SIZE//SAMPLE_SIZE):
            #t,p, als,white, r,g,b,w = struct.unpack('ffHHHHHH', buf[page*PAGE_SIZE + i*SAMPLE_SIZE: page*PAGE_SIZE + i*SAMPLE_SIZE + SAMPLE_SIZE])
            d = struct.unpack('ffHHHHHH', buf[page*PAGE_SIZE + i*SAMPLE_SIZE: page*PAGE_SIZE + i*SAMPLE_SIZE + SAMPLE_SIZE])
            #print('{:.3f}, {:.2f}, {}, {}, {}, {}, {}, {}'.format(t,p,als,white,r,g,b,w))
            if any([math.isnan(dd) for dd in d]):
                good = False
                break
            D.append(d)
            
    except KeyboardInterrupt:
        break

# reconstruct time axis using logging start time and sample interval
print('Reading config {}'.format(configfilename))
config = json.loads(open(configfilename).read())
start_time = config['start_time']

print('Reconstructing time axis...')
ts = np.linspace(0, len(D) - 1, num=len(D))
ts *= SAMPLE_INTERVAL_S
ts += start_time
#print(ts[0:10])
#sys.exit()

DT = list(zip(*D))
DT.insert(0, ts)
D = zip(*DT)

print('Writing to {}...'.format(outputfilename))
with open(outputfilename, 'w', newline='') as fout:
    writer = csv.writer(fout, delimiter=',')
    for d in D:
        writer.writerow([str(x) for x in d])

#ts, t,p, als,white, r,g,b,w = zip(*D)

print('Done.')
