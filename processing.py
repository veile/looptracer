import numpy as np
from scipy.integrate import trapezoid, cumulative_trapezoid
from scipy.interpolate import interp1d

def find_nearest_idx(array, value):
    array = np.asarray(array)
    return (np.abs(array - value)).argmin()


def reconstruct(f, R, P, mag_transfer, phase_transfer, control_coil=False):
    # Removing nan values
    f = f[~np.isnan(f)]
    R = R[~np.isnan(R)]
    P = P[~np.isnan(P)]


    # Normalize by numbers of frequencies
    norm = np.ones(f.size)
    idx = np.append([0], np.where(np.diff(f) > 1)[0]+1)
    # norm[idx] = np.append(np.diff(idx), f.size-idx[-1])

    if control_coil:
        mag_transfer = lambda f: 1
        phase_transfer = lambda f: 0

    def S(time):
        amplitude = np.sqrt(2) * R / mag_transfer(f)
        phase = np.exp(1j * P) * np.exp(1j * phase_transfer(f))

        return np.sum(1*amplitude * phase * np.exp(1j * 2 * np.pi * np.outer(time, f)), axis=1).imag

    return lambda t: S(t)


class CoilSignal:
    def __init__(self, R, P, f):
        """
        :numpy.array t: time signal in seconds
        :numpy.array pickup_signal: voltage signal from pickup coil (magnetic moment)
        :numpy.array control_signal: voltage signal from control coil (applied field)

        Signals should only be for 1 period
        Function should be adjusted for the format of future undecided convention
        """

        self.R = R
        self.P = P
        self.f = f

    def reconstruct(self, frequency, mag_transfer, phase_transfer, control_coil=False):
        # Interpolate magnitude and phase values
        magnitude_transfer = interp1d(frequency, mag_transfer)
        phase_transfer = interp1d(frequency, phase_transfer / 180 * np.pi)

        if control_coil:
            magnitude_transfer = lambda f: 1
            phase_transfer = lambda f: 0

        def S(time):
            amplitude = np.sqrt(2) * self.R / magnitude_transfer(self.f)
            phase = np.exp(1j * self.P) * np.exp(1j * phase_transfer(self.f))

            return np.sum(amplitude * phase * np.exp(1j * 2 * np.pi * np.outer(time, self.f)), axis=1).imag

        return lambda t: S(t)

class HysCurve:
    def __init__(self, sample_signal, blank_signal, cal_x, cal_y):
        """
        :CoilSignal sample_signal:
        :CoilSignal blank_signal:
        :float cal_x: Calibration factor between Vc and field strength
        :float cal_y: Calibration factor between Vp and moment strength
        """
        self.SS = sample_signal
        self.BS = blank_signal

        # Removing background noise based on blank measurement
        # if self.SS.Vp.max() > self.BS.Vp.max():
        #     self.SS.Vp = self.SS.Vp - self.BS.Vp
        # else:
        #     self.SS.Vp = self.BS.Vp - self.SS.Vp
        #
        self.SS.Vp = self.SS.Vp - self.BS.Vp


        # self.X = self.SS.Vc
        # self.Y = self.SS.Vp

        # Centering the loop in x- and y-direction (control and pickup direction)
        offset_x = np.mean(self.SS.Vc)
        offset_y = np.mean(self.SS.Vp)

        self.Y = (self.SS.Vp - offset_y)
        self.X = (self.SS.Vc - offset_x)