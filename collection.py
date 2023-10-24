import time
import numpy as np
import zhinst.core

from scipy.interpolate import interp1d
from devices import PowerSupply

class LockInAmplifier():
    """
    https://docs.zhinst.com/labone_programming_manual/low_level_commands.html
    """
    def __init__(self, hostname='mf-dev6832.local', server_port=8004, api_level=6):
        self.daq = zhinst.core.ziDAQServer(hostname, server_port, api_level)

        self.name = hostname[hostname.find('d'):hostname.find('d')+7]

        self.daq.setDouble(f'/{self.name}/demods/0/rate', 1e3)
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
        self.daq.setInt(f'/{self.name}/sigins/0/imp50', 1)

        self.sleep_sync= 0.1 #10 * self.timeconstant
        self.poll_length = 0.05  # [s]
        self.sleep_data = 0.1 # Swapped between sync and data

        # Wait for the demodulator filter to settle.
        self.daq.unsubscribe("*")
        time.sleep(self.sleep_sync)
        self.daq.sync()

    # Legacy method
    def retrieve_signals(self):
        Rc, Pc, fc = self.retrieve_vc()
        Rp, Pp, fp = self.retrieve_vp()

        return Rc, Pc, fc, Rp, Pp, fp
        # return self.t, Vp, Vc, self.freq

    def retrieve_vc(self):
        # Measure control coil signal
        self.daq.setInt(f'/{self.name}/demods/0/adcselect', 8)
        self.daq.setInt(f'/{self.name}/demods/0/harmonic', 1)
        time.sleep(self.sleep_sync)
        self.daq.sync()

        self.daq.subscribe(f'/{self.name}/demods/0/sample')
        time.sleep(self.sleep_data)
        data = self.daq.poll(self.poll_length, timeout_ms=500, flat=True)
        self.daq.unsubscribe('*')

        X = data[f'/{self.name}/demods/0/sample']['x'].mean()
        Y = data[f'/{self.name}/demods/0/sample']['y'].mean()

        R = np.abs(X + 1j * Y)
        P = np.angle(X + 1j * Y)
        return R, P, self.freq
        # return self._reconstruct(R, P, [self.freq], control_coil=True)

    def retrieve_vp(self):
        # Number of harmonics measured
        N = int(5e6 // self.freq)+1

        # Pickup coil signal
        self.daq.setInt(f'/{self.name}/demods/0/adcselect', 0)
        # Demodulated Amplitude R and phase P
        R = np.array([])
        P = np.array([])
        f = np.array([])
        for n in range(1, N):
            print(f'Measuring harmonics {n} out of {N-1}...')
            self.daq.setInt(f'/{self.name}/demods/0/harmonic', n)

            # Wait for the demodulator filter to settle.
            time.sleep(self.sleep_sync)
            self.daq.sync()

            f = np.append(f, self.daq.getDouble(f'/{self.name}/demods/0/freq'))

            self.daq.subscribe(f'/{self.name}/demods/0/sample')
            time.sleep(self.sleep_data)
            data = self.daq.poll(self.poll_length, timeout_ms=500, flat=True)
            self.daq.unsubscribe(f'/{self.name}/demods/0/sample')

            x = data[f'/{self.name}/demods/0/sample']['x']
            y = data[f'/{self.name}/demods/0/sample']['y']

            r = np.abs(x+1j*y)
            p = np.angle(x+1j*y)

            R = np.append(R, r.mean())
            print(r[0], r[-1])
            P = np.append(P, p.mean())

        return R, P, f
        # # Reconstructed Signal
        # Vp = self._reconstruct(R, P, f)
        #
        # return Vp

    def calibrate_field(self, file, COM, capacitance='200 nF'):
        try:
            max_current = {'200 nF': 28, '88 nF': 23,  '26 nF': 20, '15 nF': 17, '6.2 nF': 13}[capacitance]
        except KeyError:
            raise ValueError('Capacitance input is wrongly formatted - should be a string like \'200 nF\' ')

        current = np.arange(1, max_current+1)

        # Initialising the power supply
        PS = PowerSupply(COM)

        PS.set_V(45)
        PS.set_I(0)
        PS.set_output('ON')

        with open(file, 'w') as f:
            f.write(f'# {self.freq} kHz\nCurrent [A]\tAmplitude [V]\n')

        for I in current:
            print(f"Measuring PSU A = {I}")
            PS.set_I(I)

            # Wait 2 seconds before measurement - stabilizing
            time.sleep(2)
            R, P, freq = self.retrieve_vc()
            Vc = self._reconstruct(R, P, [self.freq], control_coil=True)
            with open(file, 'a') as f:
                f.write(f'{I}\t{np.max(Vc)}\n')

        print('Finished')

        PS.set_default()

    def _reconstruct(self, R, P, f, control_coil=False):
        # Getting distortion factors
        if self.daq.get(f'/{self.name}/sigins/0/imp50'):
            cal_file = 'calib_data_03_07_2023_final_50ohms.csv'
        else:
            cal_file = 'calib_data_03_07_2023_final_hi-z.csv'

        with open(cal_file) as file:
            lines = (line for line in file if not line.startswith('#'))
            distortion = np.loadtxt(lines, delimiter=',', skiprows=1).T

        # Interpolate magnitude and phase values
        magnitude_transfer = interp1d(distortion[0], distortion[1])
        phase_transfer = interp1d(distortion[0], distortion[2]/180*np.pi)

        # Debug
        magnitude_transfer = lambda f: 1
        phase_transfer = lambda f: 0

        if control_coil:
            magnitude_transfer = lambda f: 1
            phase_transfer = lambda f: 0

        # print(P)
        # print(phase_transfer(f[0]))

        def S(time):
            amplitude = np.sqrt(2)*R/magnitude_transfer(f)
            phase = np.exp(1j*P)*np.exp(1j*phase_transfer(f))

            return np.sum(amplitude*phase*np.exp(1j*2*np.pi*np.outer(time, f)), axis=1).imag

        return S(self.t)
