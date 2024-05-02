import time
import numpy as np
import zhinst.core

from devices import PowerSupply

class LockInAmplifier():
    """
    https://docs.zhinst.com/labone_programming_manual/low_level_commands.html
    """
    def __init__(self, hostname='mf-dev6832.local', server_port=8004, api_level=6, imp50=1):
        self.daq = zhinst.core.ziDAQServer(hostname, server_port, api_level)

        self.name = hostname[hostname.find('d'):hostname.find('d')+7]

        self.daq.setDouble(f'/{self.name}/demods/0/rate', 1e3)
        self.rate = self.daq.getDouble(f'/{self.name}/demods/0/rate')
        self.timeconstant = self.daq.getDouble(f"/{self.name}/demods/0/timeconstant")
        self.clock = self.daq.getDouble(f'/{self.name}/clockbase')

        # Getting frequency from extrefs (Using Trigger 1 as reference)

        self.daq.setInt(f'/{self.name}/extrefs/0/enable', 1)
        self.daq.setInt(f'/{self.name}/demods/1/adcselect', 2)

        self.freq = self.daq.getDouble(f'/{self.name}/oscs/0/freq')
        self.t = np.linspace(0, 1/self.freq, 1000)

        # Ensure the device is pushing data to the data server
        # self.daq.setInt(f'/{self.name}/auxins/0/enable', 1)
        self.daq.setInt(f'/{self.name}/demods/0/enable', 1)
        self.daq.setInt(f'/{self.name}/sigins/0/imp50', imp50)

        self.sleep_sync= 0.1 #10 * self.timeconstant
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

        :return f: numpy.array of measured frequency
                x: numpy.array of measured x-component of the complex signal
                y: numpy.array of measured y-component of the complex signal
        '''
        self.daq.setInt(f'/{self.name}/demods/0/adcselect', adcselect)

        # Wait for demodulator filter to settle
        time.sleep(self.sleep_sync)
        self.daq.sync()

        self.daq.subscribe(f'/{self.name}/demods/0/sample')
        time.sleep(self.sleep_data)
        data = self.daq.poll(self.poll_length, timeout_ms=500, flat=True)
        self.daq.unsubscribe('*')

        x = data[f'/{self.name}/demods/0/sample']['x']
        y = data[f'/{self.name}/demods/0/sample']['y']
        f = data[f'/{self.name}/demods/0/sample']['frequency']

        return f, x, y

    # Legacy method
    def retrieve_signals(self, harmonics = 'all'):
        Rc, Pc, fc = self.retrieve_vc()
        Rp, Pp, fp = self.retrieve_vp(harmonics=harmonics)

        return Rc, Pc, fc, Rp, Pp, fp

    def retrieve_vc(self):
        # Measure control coil signal
        self.daq.setInt(f'/{self.name}/demods/0/harmonic', 1)

        freq, X, Y = self.retrieve_signal(adcselect=8)

        R = np.abs(X + 1j * Y)
        P = np.angle(X + 1j * Y)
        return R, P, freq

    def retrieve_vp(self, harmonics='all'):
        if harmonics == 'all':
            # Number of harmonics measured
            N = int(5e6 // self.freq)+1
        else:
            N = int(harmonics)

        # Demodulated Amplitude R and phase P
        R = np.array([])
        P = np.array([])
        freqs = np.array([])

        # Only measuring odd harmonics
        for n in range(1, N, 2):
            print(f'Measuring harmonics {n} out of {N-1}...')
            self.daq.setInt(f'/{self.name}/demods/0/harmonic', n)

            f, x, y = self.retrieve_signal(adcselect=0)

            r = np.abs(x+1j*y)
            p = np.angle(x+1j*y)

            freqs = np.append(freqs, f)
            R = np.append(R, r)
            P = np.append(P, p)

        return R, P, freqs

    def distortion_corection(self, pts=50):
        freqs = np.geomspace(1e5, 5e6, pts)

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
            _, ix, iy = self.retrieve_signal(adcselect=1)
            i = ix + 1j*iy

            # Retrieve voltage
            _, vx, vy = self.retrieve_signal(adcselect=0)
            v = vx + 1j*vy

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


    # def calibrate_field(self, file, COM, capacitance='200 nF'):
    #     try:
    #         max_current = {'200 nF': 28, '88 nF': 23,  '26 nF': 20, '15 nF': 17, '6.2 nF': 13}[capacitance]
    #     except KeyError:
    #         raise ValueError('Capacitance input is wrongly formatted - should be a string like \'200 nF\' ')
    #
    #     current = np.arange(1, max_current+1)
    #
    #     # Initialising the power supply
    #     PS = PowerSupply(COM)
    #
    #     PS.set_V(45)
    #     PS.set_I(0)
    #     PS.set_output('ON')
    #
    #     with open(file, 'w') as f:
    #         f.write(f'# {self.freq} kHz\nCurrent [A]\tAmplitude [V]\n')
    #
    #     for I in current:
    #         print(f"Measuring PSU A = {I}")
    #         PS.set_I(I)
    #
    #         # Wait 2 seconds before measurement - stabilizing
    #         time.sleep(2)
    #         R, P, freq = self.retrieve_vc()
    #         Vc = self._reconstruct(R, P, [self.freq], control_coil=True)
    #         with open(file, 'a') as f:
    #             f.write(f'{I}\t{np.max(Vc)}\n')
    #
    #     print('Finished')
    #
    #     PS.set_default()