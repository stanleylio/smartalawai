import json, logging, sys, string, struct, time, math
from dev.crc_check import check_response

logger = logging.getLogger(__name__)

class Kiwi:
    SPI_FLASH_SIZE_BYTE = 16*1024*1024
    SPI_FLASH_PAGE_SIZE_BYTE = 256
    SPI_FLASH_PAGE_COUNT = SPI_FLASH_SIZE_BYTE/SPI_FLASH_PAGE_SIZE_BYTE
   
    def __init__(self, ser):
        self._ser = ser
        self._version = None
        self._config = None
        
        self.identify_version()
        logger.debug('Version={}'.format(self._version))

        self.get_config()
        logger.debug(self._config)

        self.sample_struct_fmt = 'ffHHHHHH' if self._config['use_light'] else 'ff'
        self.SAMPLE_SIZE_BYTE = struct.calcsize(self.sample_struct_fmt)
        self.SAMPLE_PER_PAGE = Kiwi.SPI_FLASH_PAGE_SIZE_BYTE//self.SAMPLE_SIZE_BYTE

    def identify_version(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        try:
            self._ser.write(b'id')
            r = self._ser.readline()
            logger.debug(r)
            d = json.loads(r.decode().strip())
            self._version = d['ver']
            return self._version
        except (UnicodeDecodeError, IndexError, TypeError, ValueError):
            pass

        try:
            self._ser.write(b'is_logging')
            r = self._ser.readline()
            logger.debug(r)
            if 3 == len(r.decode().strip().split(',')):
                self._version = 0
                return self._version
        except (UnicodeDecodeError, IndexError, TypeError, ValueError):
            pass

        return self._version

    def get_config(self, *_, use_cached=False):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        if use_cached and self._config is not None:
            return self._config
        
        if 0 == self._version:
            self._ser.write(b'get_logging_config')
            r = self._ser.readline()
            logger.debug(r)
            if not len(r):
                return None
            r = r.decode().strip().split(',')
            config = {
                'start':int(r[0]),
                'stop':int(r[1]),
                'interval_ms':{'0':200, '1':1000, '2':60000}[r[2]]}

            self._ser.write(b'get_logger_name')
            r = self._ser.readline().strip()
            logger.debug(r)
            config['name'] = r.decode() if not all([0xff == b for b in r]) else ''
            config['use_tsys01'] = 1
            config['use_tmp117'] = 0
            config['use_light'] = 1
            config['rt_output'] = 0

            self._ser.write(b'spi_flash_get_unique_id')
            r = self._ser.readline()
            logger.debug(r)
            r = r.decode().strip()
            if 16 != len(r) or not r.startswith('E') or not all([c in string.hexdigits for c in r]):
                logger.warning('Serial number ain\'t right...')
            config['id'] = r

            self._config = config
        else:
            try:
                self._ser.write(b'get_config')
                r = self._ser.readline()
                logger.debug(r)
                config = json.loads(r.decode().strip())
                if 'stop' not in config:
                    config['stop'] = None

                self._ser.write(b'id')
                r = self._ser.readline()
                logger.debug(r)
                config['id'] = json.loads(r.decode().strip())['id']
                self._config = config
            except json.decoder.JSONDecodeError:
                logger.debug(r)
                if 0 == len(r):
                    logger.warning('No response from anything.')
                raise RuntimeError('Could not get config from logger.')

        return self._config

    def is_logging(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        if 0 == self._version:
            self._ser.write(b'is_logging')
            r = self._ser.readline()
            logger.debug(r)
            r = r.decode().strip().split(',')
            if len(r) == 3 and r[0] in ['0', '1']:
                return '1' == r[0]
        else:
            self._ser.write(b'status')
            r = self._ser.readline()
            logger.debug(r)
            return 1 == json.loads(r.decode().strip())['is_logging']

    def get_battery_voltage(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        if 0 == self._version:
            self._ser.write(b'read_sys_volt')
            r = self._ser.readline()
            logger.debug(r)
            r = r.decode().strip().split(',')
            return round(float(r[1]), 2)
        else:
            self._ser.write(b'status')
            d = json.loads(self._ser.readline().decode().strip())
            return float(d['Vb'])

    def get_sample_count(self):
        last_page_index = self.find_last_used_page()
        if last_page_index is None:
            return 0
        buf = self.read_page(last_page_index)
        assert not all([0xff == x for x in buf])
        # I have no idea what I wrote.
        byte_used = Kiwi.SPI_FLASH_PAGE_SIZE_BYTE - next(k for k,v in enumerate(reversed(buf)) if v not in [0, 0xff])
        # Careful, last_page_index is 0-based. The number of non-empty pages is last_page_index + 1, but
        # here you are summing up the full pages plus the bits in the last (possibly non-full) page.
        # Really it is (last_page_index + 1 - 1).
        return last_page_index*(Kiwi.SPI_FLASH_PAGE_SIZE_BYTE//self.SAMPLE_SIZE_BYTE) + byte_used//self.SAMPLE_SIZE_BYTE
        # huh. is A//X + B//X === (A + B)//X? Is the // operator distributive? Can I do
        # (last_page*SPI_FLASH_PAGE_SIZE_BYTE + byte_used)//SAMPLE_SIZE_BYTE?
        # Nope. 7//10 + 3//10 != 10//10
        # What about the associative property? The * vs. the //, does it matter if I leave out the ()?
        # It does and you must not. 2*(5//10) != (2*5)//10
        # The * takes precedence over the //, so leaving out the () would be wrong.
        # You could have just kept the sampe_per_page = SPI_FLASH_PAGE_SIZE_BYTE//SAMPLE_SIZE_BYTE line you know.

    def find_last_used_page(self):
        # in principle you only need to check the first byte. but god knows how the flash layout might change in later versions.
        is_empty = lambda s: all([0xff == x for x in s])

        def search(begin, end):
            logger.debug('search({},{})'.format(begin, end))
            
            if begin >= end:
                assert False
            elif end - begin == 1:
                #print(is_empty(self.read_page(begin)))
                #print(is_empty(self.read_page(end)))
                if not is_empty(self.read_page(begin)):
                    return begin
                else:
                    return None
            else:
                mid = int((end + begin)//2)

            if is_empty(self.read_page(mid)):
                return search(begin, mid)
            else:
                return search(mid, end)

        return search(0, Kiwi.SPI_FLASH_SIZE_BYTE//Kiwi.SPI_FLASH_PAGE_SIZE_BYTE)

    def read_page(self, page):
        #return read_range_core(ser, page*SPI_FLASH_PAGE_SIZE_BYTE, (page+1)*SPI_FLASH_PAGE_SIZE_BYTE - 1)
        begin = page*Kiwi.SPI_FLASH_PAGE_SIZE_BYTE
        end = (page+1)*Kiwi.SPI_FLASH_PAGE_SIZE_BYTE - 1
        return self.read_range_core(begin, end)

    def read_range_core(self, begin, end):
        assert end >= begin

        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        old_timeout = self._ser.timeout
        self._ser.timeout = 4
        
        expected_length = end - begin + 1 + 4
        
        if 0 == self._version:
            cmd = 'spi_flash_read_range{:x},{:x}\n'.format(begin, end)
        else:
            cmd = 'read_range{:x},{:x}\n'.format(begin, end)
        cmd = cmd.encode()
        self._ser.write(cmd)
        line = self._ser.read(expected_length)
        self._ser.timeout = old_timeout
        if len(line) != expected_length:
            logger.error('Expecting {}, got {}.'.format(expected_length, len(line)))
            return []
        if not check_response(line):
            logger.error('CRC failure')
            return []

        return line[:-4]    # strip CRC32

    def is_empty(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        r = self.read_range_core(0, 63)
        if r is None:
            # let the caller deal with that.
            raise RuntimeError
        return all([0xff == rr for rr in r])

    # given a sample index, calculate (page address, byte index within that page)
    def sampleindex2flashaddress(self, sample_index):
        return int(sample_index//self.SAMPLE_PER_PAGE), int((sample_index%self.SAMPLE_PER_PAGE)*self.SAMPLE_SIZE_BYTE)

    # given a sample index, time of the first sample, and the sample interval, calculate the sample index
    def date2sampleindex(self, ts):
        ts = dt2ts(ts) if type(ts) is datetime else ts
        return (ts - config['start'])//(config['interval_ms']/1000)

    def read_temperature(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        
        self._ser.write(b'read_temperature' if 0 == self._version else b'T')
        r = self._ser.readline()
        logger.debug(r)
        try:
            return float(r.strip().decode().replace('Deg.C', ''))
        except:
            logger.exception('')
            return float('nan')

    def read_pressure(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        
        self._ser.write(b'read_pressure' if 0 == self._version else b'P')
        r = self._ser.readline()
        logger.debug(r)
        try:
            return float(r.strip().decode().replace('kPa', ''))
        except:
            logger.exception('')
            return float('nan')
            

    def read_light(self, *_, as_dict=True):
        """in lx for all"""
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        d = []
        if 0 == self._version:
            self._ser.write(b'read_ambient_lx')
            r = self._ser.readline()
            logger.debug(r)
            d.append(float(r.decode().strip().split(',')[0].replace('lx', '')))

            self._ser.write(b'read_white_lx')
            r = self._ser.readline()
            logger.debug(r)
            d.append(float(r.decode().strip().split(',')[0].replace('lx', '')))
            
            self._ser.write(b'read_rgbw')
            r = self._ser.readline()
            logger.debug(r)
            r = [int(float(x)) for x in r.decode().strip().split(',')]
            d.extend(r)

            return dict(zip(('hdr_als', 'hdr_w', 'r', 'g', 'b', 'w'), d)) if as_dict else d
        else:
            self._ser.write(b'L')
            r = self._ser.readline()
            logger.debug(r)
            r = [float(x) for x in r.decode().strip().split(',')]

            '''# raw to lux for VEML6030
            def c(v):
                v *= 1.8432
                if v > 1e3:
                    v = 6.0135e-13*v*v*v*v - 9.3924e-9*v*v*v + 8.1488e-5*v*v + 1.0023*v;    # >1klx correction
                return v
            r[0] = c(r[0])
            r[1] = c(r[1])

            c = lambda x: 0.25168*x
            r[2] = c(r[2])
            r[3] = c(r[3])
            r[4] = c(r[4])
            r[5] = c(r[5])'''

            return dict(zip(('hdr_als', 'hdr_w', 'r', 'g', 'b', 'w'), r)) if as_dict else r

    def get_logging_interval_code(self, interval_ms):
        if 0 == self._version:
            M = {200:0, 1000:1, 60000:2}
            if interval_ms not in M:
                logger.error('Invalid interval_ms {}'.format(interval_ms))
                return None
        else:
            M = {125:125, 250:250, 500:500, 1000:1000}
            # if it's <= 1000, then there are four options;
            # if it's > 1000, then it goes in steps of 1000 up to 60000.
            if interval_ms not in M:
                if interval_ms < 1000 or interval_ms > 60000:
                    logger.error('Invalid interval_ms {}'.format(interval_ms))
                    return None
                else:
                    interval_ms = (interval_ms//1000)*1000
                    M[interval_ms] = interval_ms
        return M[interval_ms]

    def set_logging_interval(self, interval_ms):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        code = self.get_logging_interval_code(interval_ms)
        logger.debug(code)
        self._ser.write('set_logging_interval{}\r\n'.format(code).encode('utf-8'))
        if 0 != self._version:
            tmp = 'OK' == self._ser.readline().decode().strip()
        else:
            tmp = True
        return tmp and self.get_config(use_cached=False)['interval_ms'] == interval_ms

    def start_logging(self):
        if 0 == self._version:
            self._ser.write(b'start_logging')
        else:
            self._ser.write(b'rt0')
            self._ser.readline()  # "OK\r\n"
            self._ser.write('start_logging{}\n'.format(int(time.time())).encode('utf-8'))
            self._ser.readline()  # "OK\r\n"

        time.sleep(0.2)
        return self.is_logging()

    def stop_logging(self):
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

        self._ser.write(b'stop_logging')
        self._ser.flushOutput()
        if 0 != self._version:
            #'OK' == self._ser.readline().decode().strip()
            self._ser.readline()

    def read_rtc(self):
        if 0 == self._version:
            self._ser.write(b'read_rtc')
            return float(self._ser.readline().decode().strip())
        else:
            logger.warning('Deprecated')
            return time.time()

    def set_rtc_aligned(self):
        if 0 == self._version:
            # sync to the 10 millisecond? just for fun. the RTC only has 1s resolution.
            # there's no way to start/restart the RTC's internal one-second period on trigger.
            for _ in range(2000):
                currenttime = time.time()
                if math.floor(currenttime*100)%100 == 0:      # it has just turned x.00y...
                    return float(self.set_rtc())
                else:
                    time.sleep(0.001)
            else:
                assert False, 'wut?'

        else:
            logger.debug('No-op for newer versions.')
            return time.time()

    def set_rtc(self, *_, t=None):
        if 0 == self._version:
            if t is None:
                t = time.time()
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write('write_rtc{}\n'.format(math.floor(t)).encode())
            return self._ser.readline().decode()
        else:
            logger.warning('Deprecated')
            return str(int(time.time()))


if '__main__' == __name__:

    import serial

    logging.basicConfig(level=logging.DEBUG)

    with serial.Serial('COM6', 115200, timeout=1) as ser:
        kiwi = Kiwi(ser)
        print('Logger is{} logging.'.format('' if kiwi.is_logging() else ' not'))
        print(kiwi.get_config())
        #print(kiwi.get_config(use_cached=True))
        print('{:.1f} V battery'.format(kiwi.get_battery_voltage()))
        #print(kiwi.find_last_used_page())
        print('{} samples in logger.'.format(kiwi.get_sample_count()))

        print('Logger is{} empty.'.format('' if kiwi.is_empty() else ' not'))
        print(kiwi.read_temperature())
        print(kiwi.read_pressure())
        print(kiwi.read_light())

