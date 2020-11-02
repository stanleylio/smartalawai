# Read all sensors and plot in real-time.
#
# Stanley H.I. Lio
# hlio@hawaii.edu
# MESHLAB, UH Manoa
import logging, math
from serial import Serial
from kiwi import Kiwi
from datetime import datetime
from common import dt2ts
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter


logging.basicConfig(level=logging.WARNING)

fn = 'read_sensors_output.csv'

# find the serial port to use from user, from history, or make a guess
# if on Windows, print the list of COM ports
from common import serial_port_best_guess, save_default_port
DEFAULT_PORT = serial_port_best_guess(prompt=True)
PORT = input('PORT=? (default={}):'.format(DEFAULT_PORT)).strip()
# empty input, use default
if '' == PORT:
    PORT = DEFAULT_PORT

with Serial(PORT, 115200, timeout=1) as ser,\
     open(fn, 'a', 1) as fout:

    save_default_port(PORT)

    kiwi = Kiwi(ser)

    #tags = ['T_Deg\u00B0C', 'P_kPa', 'ambient_lux', 'ambient_white_lux', 'R_lux', 'G_lux', 'B_lux', 'W_lux']
    D = []
    while True:

        t, p, als_raw, als_white_raw, r, g, b, w = [float('nan')]*8

        t = kiwi.read_temperature()
        p = kiwi.read_pressure()
        als_raw, als_white_raw, r, g, b, w = kiwi.read_light(as_dict=False)

        if all(math.isnan(v) for v in [t, p, als_raw, als_white_raw, r, g, b, w]):
            logging.debug('(all failed)')
            continue

        dt = datetime.now()
        tmp = [dt, t, p, als_raw, als_white_raw, r, g, b, w]
        D.append(list(tmp))
        tmp.insert(0, dt2ts(tmp[0]))
        fout.write(','.join([str(v) for v in tmp]) + '\n')

        if len(D) < 1:
            continue
        
        DT, T, P, ALS_RAW, ALS_WHITE_RAW, R, G, B, W = list(zip(*D))
        
        plt.clf()

        ax1 = plt.subplot(411)
        plt.plot(DT, T, 'r.:', label='{:.3f} ℃'.format(t))
        #plt.annotate('{:.3f} Deg.C'.format(t), (0.6*len(D), t), size=20)
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.ylabel('Deg\u00B0C')
        plt.legend(loc=2)
        plt.grid(True)

        ax2 = plt.subplot(412, sharex=ax1)
        plt.plot(DT, P, '.:', label='{:.2f} kPa'.format(p))
        #plt.annotate('{:.2f}'.format(p), (0.6*len(D), p), size=20)
        plt.setp(ax2.get_xticklabels(), visible=False)
        plt.ylabel('kPa')
        plt.legend(loc=2)
        plt.grid(True)

# these are uint16, but I want to be able to use float('nan') when necessary, hence {:.0f} instead of {:d}
        ax3 = plt.subplot(413, sharex=ax1)
        plt.plot(DT, ALS_RAW, '.:', label='HDR_ALS: {:.0f}'.format(als_raw), alpha=0.5)
        #plt.annotate('{:d}'.format(als_raw), (0.5*len(D), als_raw), size=20)
        plt.plot(DT, ALS_WHITE_RAW, '.:', label='HDR_W: {:.0f}'.format(als_white_raw), alpha=0.5)
        #plt.annotate('{:d}'.format(als_white_raw), (0.6*len(D), als_white_raw), size=20)
        plt.setp(ax3.get_xticklabels(), visible=False)
        plt.ylabel('(raw count)')
        plt.legend(loc=2)
        plt.grid(True)

        plt.subplot(414, sharex=ax1)
        plt.plot(DT, R, 'r.:', label='R: {:.0f}'.format(r), alpha=0.5)
        #plt.annotate('{:d}'.format(r), (0.4*len(D), r), color='r', size=20)
        plt.plot(DT, G, 'g.:', label='G: {:.0f}'.format(g), alpha=0.5)
        #plt.annotate('{:d}'.format(g), (0.5*len(D), g), color='g', size=20)
        plt.plot(DT, B, 'b.:', label='B: {:.0f}'.format(b), alpha=0.5)
        #plt.annotate('{:d}'.format(b), (0.6*len(D), b), color='b', size=20)
        plt.plot(DT, W, 'k.:', label='W: {:.0f}'.format(w), alpha=0.2)
        #plt.annotate('{:d}'.format(w), (0.7*len(D), w), color='k', size=20)
        plt.ylabel('(raw count)')

        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d %H:%M:%S'))
        #plt.xlabel('Time')
        plt.legend(loc=2)
        plt.grid(True)

        plt.pause(0.001)

        while len(D) > 1000:
            D.pop(0)
