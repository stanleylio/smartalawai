# Convert a flash dump (.bin) file to a CSV file.
#
# Data are taken from "[ID].bin"
# Timestamps are reconstructed from the config file "[ID].config"
# Output will be named "[ID].csv"
#
# MESH Lab
# University of Hawaii
# Copyright 2018 Stanley H.I. Lio
# hlio@hawaii.edu
import struct, math, sys, csv, json, logging
from glob import glob
from os.path import join, exists, basename, isdir, isfile
import numpy as np
from scipy.stats import describe
from common import SAMPLE_INTERVAL_CODE_MAP, ts2dt, dt2ts


logging.basicConfig(level=logging.DEBUG)


SAMPLE_SIZE = 20    # size of one sample in byte
PAGE_SIZE = 256


def find(pattern, dironly=False, fileonly=False):
    FN = sorted(glob(pattern))
    if dironly:
        FN = list(filter(lambda x: isdir(x), FN))
    if fileonly:
        FN = list(filter(lambda x: isfile(x), FN))

    if len(FN) == 0:
        logging.debug('No file/folder fits the criteria.')
        return None
    elif len(FN) == 1:
        logging.debug('Only one file/folder fits the criteria.')
        return FN[0]
    else:
        for k,v in enumerate(FN, start=1):
            print('{}.\t{}'.format(k,v))
            
        while True:
            r = input('Your choice: ').strip()
            try:
                if int(r) >= 1 and int(r) <= len(FN):
                    return FN[int(r) - 1]
            except ValueError:
                pass


if '__main__' == __name__:

    while True:
        d = find('data/*', dironly=True)
        if d is None:
            print('No data file found. Terminating.')
            sys.exit()
        binfilename = find(join(d, '*.bin'), fileonly=True)
        if binfilename is None:
            print('No binary file found in {}. Pick another or Ctrl + C to terminate.'.format(d))
        else:
            logging.debug(binfilename)
            break
    
    # Names of the binary data file, the configuration file, and the output file
    #binfilename = 'data/{}/{}_{}.bin'.format(flash_id, flash_id, max(FNT))
    #configfilename = 'data/{}/{}_{}.config'.format(flash_id, flash_id, max(FNT))
    #outputfilename = 'data/{}/{}_{}.csv'.format(flash_id, flash_id, max(FNT))

    #binfilename = input('Input path to binary file: ').strip()
    configfilename = binfilename.rsplit('.')[0] + '.config'
    outputfilename = configfilename.rsplit('.')[0] + '.csv'

    assert exists(binfilename)
    assert exists(configfilename)
    #assert not exists(outputfilename)

    print('Data file: {}'.format(binfilename))
    print('Configuration file: {}'.format(configfilename))

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
    logging_start_time = config['logging_start_time']
    logging_stop_time = config.get('logging_stop_time', None)

    if logging_stop_time is not None and logging_stop_time > logging_start_time:
        print('{} samples from {} to {} spanning {}'.format(len(D),
                                                            ts2dt(logging_start_time),
                                                            ts2dt(logging_stop_time),
                                                            ts2dt(logging_stop_time) - ts2dt(logging_start_time)))
        print('Effective sample rate {:.3f} sample/second or an average interval of {:.3f} second'.format(
            len(D)/(logging_stop_time - logging_start_time),
            (logging_stop_time - logging_start_time)/len(D)))
    else:
        logging.warning('No record of logging_stop_time. Are the batteries good? Did someone remove power without stopping logging first?')

    logging_interval_code = config['logging_interval_code']


    print('Reconstructing time axis...')
    ts = np.linspace(0, len(D) - 1, num=len(D))
    ts *= SAMPLE_INTERVAL_CODE_MAP[logging_interval_code]
    ts += logging_start_time
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
