import numpy as np
from scipy.integrate import trapezoid, cumulative_trapezoid


def find_nearest_idx(array, value):
    array = np.asarray(array)
    return (np.abs(array - value)).argmin()


class CoilSignals:
    def __init__(self, t, pickup_signal, control_signal, freq):
        """
        :numpy.array t: time signal in seconds
        :numpy.array pickup_signal: voltage signal from pickup coil (magnetic moment)
        :numpy.array control_signal: voltage signal from control coil (applied field)

        Signals should only be for 1 period
        Function should be adjusted for the format of future undecided convention
        """

        # Extracts the first period
        self.T = 1 / freq

        # end = find_nearest_idx(t-t[0], self.T)

        # Makes sure only complete periods exists (working with multiple periods)
        # end = int(np.floor(t.size - (t[-1] % self.T)))

        self.t = t#[:end]
        self.Vp = pickup_signal#[:end]
        self.Vc = control_signal#[:end]

        self.remove_dc_bias()
        self.integrate()

    def remove_dc_bias(self):
        """
        Integrating a period of the signal should average to 0.
        This function removes any DC bias to ensure this.
        """
        integral_p = trapezoid(self.Vp, self.t)
        integral_c = trapezoid(self.Vc, self.t)

        dc_p = integral_p / self.T
        dc_c = integral_c / self.T

        self.Vp = self.Vp - dc_p
        self.Vc = self.Vc - dc_c

    def integrate(self):
        self.Vp = cumulative_trapezoid(self.Vp, self.t, initial=0)
        self.Vc = cumulative_trapezoid(self.Vc, self.t, initial=0)

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

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import pandas as pd

    def load_xlsx(filename):
        df = pd.read_excel(filename)
        t = np.array(df['X'].iloc[1:], dtype=float)
        Vp = np.array(df['CH4'].iloc[1:], dtype=float)
        Vc = -np.array(df['CH3'].iloc[1:], dtype=float)

        return CoilSignals(t, Vp, Vc, rate=1e-8, freq=160.6e3)


    sample = load_xlsx('10_with_sample_26Amps_160-6-kHz-36-2-V_1024_avg.xlsx')
    blank = load_xlsx('11_no_sample_26Amps_160-6-kHz-36-2-V_1024_avg.xlsx')

    H = HysCurve(sample, blank, 1, 1)

    fig, ax = plt.subplots()

    ax.plot(sample.t, sample.Vp)
    ax2 = ax.twinx()
    ax2.plot(sample.t, sample.Vc, c='C1')

    plt.show()

    fig, ax = plt.subplots()
    ax.plot(H.X, H.Y)
    plt.show()


