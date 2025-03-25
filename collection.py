import time
import threading
import numpy as np
import zhinst.core
import os

from devices import PowerSupply, fiber


class Signal:
    """
    Object containing all the information about a retrieved signal
    """
    def __init__(self, t, f, x, y, settings):
        self.t = t
        self.f = f
        self.x = x
        self.y = y
        self.settings = settings

        self.z = x + 1j*y
        self.r = np.abs(self.z)
        self.p = np.angle(self.z)

class LockInAmplifier:
    """
    https://docs.zhinst.com/labone_programming_manual/low_level_commands.html
    """
    def __init__(self, hostname='mf-dev6832', server_port=8004, api_level=6, imp50=1):
        self.daq = zhinst.core.ziDAQServer(hostname, server_port, api_level)

        self.name = hostname[hostname.find('d'):hostname.find('d')+7]

        # Synchronizing system time with timestamps
        # To get system time at later timestamps, one needs to find elapsed time in seconds:
        # new_sytemtime = start_systemtime + (timestamp*dt - self.start_timestamp)*1e-9
        self.dt = self.daq.getDouble(f'/{self.name}/system/properties/timebase')
        self.start_timestamp = self.daq.getInt(f'/{self.name}/status/time') * self.dt  # Timestamp in ns since device power on
        self.start_systemtime = time.time()  # UTC in s


        self.daq.setDouble(f'/{self.name}/demods/0/rate', 1e3)
        self.rate = self.daq.getDouble(f'/{self.name}/demods/0/rate')
        self.timeconstant = self.daq.getDouble(f"/{self.name}/demods/0/timeconstant")
        self.clock = self.daq.getDouble(f'/{self.name}/clockbase')

        # Getting frequency from extrefs (Using AUX IN 1 (8) as reference)
        self.daq.setInt(f'/{self.name}/extrefs/0/enable', 1)
        self.daq.setInt(f'/{self.name}/demods/1/adcselect', 8)

        # Ensure the device is pushing data to the data server
        # self.daq.setInt(f'/{self.name}/auxins/0/enable', 1)
        self.daq.setInt(f'/{self.name}/demods/0/enable', 1)
        self.daq.setInt(f'/{self.name}/sigins/0/imp50', imp50)
        self.daq.setInt(f'/{self.name}/demods/0/harmonic', 1)
        self.daq.setInt(f'/{self.name}/demods/0/phaseshift', 0)


        # Filter settings
        self.daq.setDouble(f'/{self.name}/demods/0/timeconstant', 0.000138458257)
        self.daq.setDouble(f'/{self.name}/demods/1/timeconstant', 0.000138458257)

        self.freq = self.daq.getDouble(f'/{self.name}/oscs/0/freq')
        self.t = np.linspace(0, 1/self.freq, 1000)

        self.sleep_sync = 0.1 #10 * self.timeconstant
        self.poll_length = 0.05  # [s]
        self.sleep_data = 0.1 # Swapped between sync and data

        # Wait for the demodulator filter to settle.
        self.daq.unsubscribe("*")
        time.sleep(self.sleep_sync)
        self.daq.sync()

    def get_settings(self):
        d1 = self.daq.get(f'/{self.name}/demods', flat=True)
        d2 = self.daq.get(f'/{self.name}/sigins', flat=True)
        d1.update(d2)

        return d1

    def retrieve_signal(self, adcselect):
        '''
        :param adcselect: integer from 0-9 that selects the input port
        0 - Sig In 1
        1 - Curr In 1
        2 - Trigger 1
        3 - Trigger 2
        4 - Aux Out 1
        5 - Aux Out 2
        6 - Aux Out 3
        7 - Aux Out 4
        8 - Aux In 1
        9 - Aux In 2

        :return
                systemtime: numpy.array of Python time() - UTC seconds since Jan 1 1970
                f: numpy.array of measured frequency
                x: numpy.array of measured x-component of the complex signal
                y: numpy.array of measured y-component of the complex signal
                settings: dictionary of lock-in amplifier settings
        '''
        self.daq.setInt(f'/{self.name}/demods/0/adcselect', adcselect)

        # Wait for demodulator filter to settle
        # time.sleep(self.sleep_sync)
        self.daq.sync()

        self.daq.subscribe(f'/{self.name}/demods/0/sample')
        # time.sleep(self.sleep_data)
        # Getting settings will take a bit of time, in which the data buffer will acquire data.
        settings = self.get_settings()
        data = self.daq.poll(self.poll_length, timeout_ms=500, flat=True)
        self.daq.unsubscribe('*')

        # Synchronizing the timestamp with Python UTC time
        timestamp = data[f'/{self.name}/demods/0/sample']['timestamp']
        systemtime = self.start_systemtime + (timestamp*self.dt - self.start_timestamp)

        x = data[f'/{self.name}/demods/0/sample']['x']
        y = data[f'/{self.name}/demods/0/sample']['y']
        f = data[f'/{self.name}/demods/0/sample']['frequency']

        return Signal(systemtime, f, x, y, settings)

    def save_signal(self, signal, filename):
        # Checking data for outliers, taking mean and saving
        t = signal.t
        f = signal.f
        x = signal.x
        y = signal.y

        # Outlier detection - Maybe this should be implemented in the Signal class
        outliers = (np.abs(x-x.mean()) > 3*x.std()) | (np.abs(y-y.mean()) > 3*y.std())
        if outliers.sum() > 0:
            print(f'Found {outliers.sum()} outliers out of {x.size}')
            t = t[~outliers]
            f = f[~outliers]
            x = x[~outliers]
            y = y[~outliers]

        if not os.path.exists(filename):
            with open(filename, 'w') as file:
                settings_header = ''
                for key, item in signal.settings.items():
                    settings_header += f'\t{key}'

                file.write(f'Time UTC\tf\tx\ty' + settings_header + '\n')

        with open(filename, 'a') as file:
            # Constructing settings string:
            settings_str = ''
            for key, item in signal.settings.items():
                settings_str += f'{item["value"][0]}\t'

            file.write(f'{t.mean()}\t{f.mean()}\t{x.mean()}\t{y.mean()}\t'+settings_str+'\n')

        return None

    def retrieve_vc(self, filename):
        # Measure control coil signal
        self.daq.setInt(f'/{self.name}/demods/0/harmonic', 1)

        signal = self.retrieve_signal(adcselect=8)
        self.save_signal(signal=signal, filename=filename)

        return signal

    def retrieve_vp(self, filename, harmonics='all'):
        if harmonics == 'all':
            # Number of harmonics measured
            N = int(5e6 // self.freq)+1
        else:
            N = int(harmonics)

        signals = []
        # Only measuring odd harmonics
        for n in range(1, N, 2):
            # print(f'Measuring harmonics {n} out of {N-1}...')
            self.daq.setInt(f'/{self.name}/demods/0/harmonic', n)

            signal = self.retrieve_signal(adcselect=0)
            signals.append(signal)
            self.save_signal(signal, filename)

        return signals

    def distortion_correction(self, pts=50):
        # Creating a frequency space that is extra dense around the frequencies of interest. (only 1 harmonic)
        interest_points = [160.6e3, 241e3, 404e3, 570.6e3, 922.7e3]
        freqs = [np.geomspace(100e3, 5e6, pts)] +\
                [np.geomspace(p - 5e3, p+ 5e3, int(pts/5)) for p in interest_points]
        freqs = np.unique(np.concatenate(freqs))

        # Use internal oscillator as reference
        self.daq.setInt(f'/{self.name}/demods/0/harmonic', 1)
        self.daq.setInt(f'/{self.name}/extrefs/0/enable', 0)

        # Turn on output signal
        self.daq.setDouble(f'/{self.name}/sigouts/0/amplitudes/1', 0.6)
        self.daq.setInt(f'/{self.name}/sigouts/0/on', 1)

        I, V = np.array([]), np.array([])
        for f in freqs:
            self.daq.setDouble(f'/{self.name}/oscs/0/freq', f)
            print(f'{f/1e3} kHz')

            # Retrieve current
            signal_i = self.retrieve_signal(adcselect=1)
            i = signal_i.z

            # Retrieve voltage
            signal_v = self.retrieve_signal(adcselect=0)
            v = signal_v.z

            # Accounting for possible different sizes of v and i:
            if v.size < i.size:
                i = i[:v.size]
            else:
                v = v[:i.size]

            # Outlier detection
            outliers = np.abs(np.abs(v)-np.abs(v).mean()) > 3*np.std(np.abs(v))

            print(f'Found {outliers.sum()} outliers out of {v.size}')

            i = i[~outliers]
            v = v[~outliers]

            I = np.append(I, i.mean())
            V = np.append(V, v.mean())

        # Turn off output signal
        self.daq.setInt(f'/{self.name}/sigouts/0/on', 0)

        return freqs, I, V


class Magnetherm:
    def __init__(self, fiber_port, psu_port):
        self.fiber = fiber(fiber_port)
        self.psu = PowerSupply(psu_port)

        self._stop_event = threading.Event()

    def measure(self):
        t = time.time()

        try:
            V = self.psu.get_V().strip('V')
            I = self.psu.get_I().strip('A')
            temperatures = '\t'.join(list(map(str, self.fiber.get_T())))

            output = f'{t}\t{I}\t{V}\t{temperatures}'

        except ValueError as e:
            # Valueerror is often caused by checksum error in the temperature probe - flushing the temperature probe
            self.fiber.reinitialize()
            output = f'{t}\t-1\t-1\t' + '\t'.join(list(map(str, [-274] * len(self.fiber))))

        return output

    def run(self, file, dt=.5):
        # Creating file
        with open(file, 'w') as f:
            Theader = "\t".join([f'T{i} [degC]' for i in range(len(self.fiber))])
            f.write(f'Time UTC\tCurrent [A]\tVoltage [V]\t' + Theader + '\n')

        # Initially sets the time to a number divisible by the sample rate
        time.sleep(dt - (time.time() % dt))
        while not self._stop_event.is_set():
            output = self.measure()
            with open(file, 'a') as f:
                f.write(output+'\n')

            # Waiting dt, taking into account the time performing previous actions
            time.sleep(dt - (time.time() % dt))

    def stop(self):
        self._stop_event.set()
