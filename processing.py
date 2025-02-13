import os
import re
import glob

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


def find_nearest_idx(array, value):
    array = np.asarray(array)
    return (np.abs(array - value)).argmin()


def unique_idx(x):
    uniques = np.unique(x, return_index=True)[1].tolist()
    return uniques + [len(x)]


def avg_array(x, idx):
    return np.array([x[idx[i]:idx[i + 1]].mean() for i in range(len(idx) - 1)])


def get_distortion_correction(f, I, V):
    f = np.abs(f)
    # The expected voltage is equal to frequency, current and some coil property constant.
    # The constant is not important as we calibrate the system later.
    Vexp = f * np.abs(I)
    # print(Vexp)
    # Magnitude transfer denotes the attenuation/rise of the true voltage due to the pick-up coils.
    # This constant needs to be multiplied onto the measured voltage
    mag_transfer = Vexp / np.abs(V)

    # Phase transfer denotes the phase shift imposed by the pick-up system
    # The phase shift needs to be added onto the measured phase.
    # A coil has the voltage V = L dI/dt, so the expected voltage is 90 degree shifted from the current
    Pexp = np.angle(I * np.exp(-1j * np.pi / 2))

    # This is to correctly add angles
    # pi is added to get the phase in range of 0 - 2pi to use modulus and then subtract eh pi again.
    # phase_transfer = (Pexp - np.angle(V) +np.pi) % (2*np.pi) - np.pi
    phase_transfer = np.angle(np.exp(1j * Pexp) * np.exp(-1j * np.angle(V)))
    # phase_transfer = Pexp - np.angle(V)

    return interp1d(f, mag_transfer), interp1d(f, phase_transfer)


def get_coeff(df, mag_transfer=lambda f: 1, phase_transfer=lambda f: 0, phase_correction=0):
    # Pickup signal
    f = df['Blank Pickup f']
    R = df['Blank Pickup R']
    P = df['Blank Pickup P']

    fS = df['Sample Pickup f']
    RS = df['Sample Pickup R']
    PS = df['Sample Pickup P']

    # Control signal
    f_C = df['Blank Control f']
    R_C = df['Blank Control R']
    P_C = df['Blank Control P']

    fS_C = df['Sample Control f']
    RS_C = df['Sample Control R']
    PS_C = df['Sample Control P']

    n = df['Sample Pickup /dev6832/demods/0/harmonic']
    repeats = df['repeats']

    # Applying same blank to all measurements
    f, R, P = np.tile(f, repeats), np.tile(R, repeats), np.tile(P, repeats)
    f_C, R_C, P_C = np.tile(f_C, repeats), np.tile(R_C, repeats), np.tile(P_C, repeats)

    # Phase distortion correction and phase correction
    P = np.angle(np.exp(1j * (P + phase_transfer(f))))
    PS = np.angle(np.exp(1j * (PS + phase_transfer(fS))))

    # Applied field
    Hv = np.sqrt(2) * RS_C / (2 * np.pi * fS_C)
    ϕv = np.angle(np.exp(1j * (PS_C + np.pi / 2)))
    # ϕv = np.pi/2

    # # Magnetic Moment
    V = np.sqrt(2) * RS * mag_transfer(fS) * np.exp(1j * PS) - \
        np.sqrt(2) * R * mag_transfer(f) * np.exp(1j * P)

    M = np.abs(V) / (2 * np.pi * fS)
    ϕ = np.angle(V * np.exp(1j * np.pi / 2 - n * phase_correction))

    return Hv, ϕv, M, ϕ


class LoopTracer():
    '''
    Attributes:
        path: filepath to folder with all experiment files
        weight: float value of sample weight in kg
        distortion: list of filepath to measured f, V, I values for a impedance that need to be specified in filename (HiZ or imp50)
        phase_correction: Dictionary with phase correction values for each capacitance
        name: string identifier saved in self.name. Defaults to folder name if not specified
    '''

    def __init__(self, path, distortion_path=None, phase_correction=0, name=None):
        self.path = path
        self.phase_correction = phase_correction

        if distortion_path:
            self.distortion = self.create_distortion_dict(distortion_path)
        else:
            self.distortion = {'imp50': {}, 'HiZ': {}}
            self.distortion['HiZ']['Mag Transfer'], self.distortion['HiZ']['Phase Transfer'] = lambda f: 1, lambda f: 0
            self.distortion['imp50']['Mag Transfer'], self.distortion['imp50']['Phase Transfer'] = lambda f: 1, lambda \
                f: 0

        self.foldername = path[path.rfind('/') + 1:]

        if name:
            self.name = name
        else:
            self.name = self.foldername

        try:
            self.df = pd.read_pickle(path + '/' + self.foldername + '.pkl')
        except IOError:
            self.create_pickle()

    def create_distortion_dict(self, file_list):
        distortion = {'imp50': {}, 'HiZ': {}}

        for file in file_list:
            f, I, V = np.loadtxt(file, dtype=complex)
            if 'HiZ' in file:
                distortion['HiZ']['Mag Transfer'], distortion['HiZ']['Phase Transfer'] = get_distortion_correction(f, I,
                                                                                                                   V)
            elif 'imp50' in file:
                distortion['imp50']['Mag Transfer'], distortion['imp50']['Phase Transfer'] = get_distortion_correction(
                    f, I, V)
            else:
                raise Exception('No impedance specified in the filename!')

        return distortion

    def create_pickle(self):
        full_filenames = [s[:-16] for s in glob.glob(self.path + '/*_#parameters.txt')]
        filenames = [os.path.basename(p) for p in full_filenames]

        # Usual experiment has (control+pickup)  * (blank+sample)
        types = {'blank_control': {}, 'blank_pickup': {}, 'sample_control': {}, 'sample_pickup': {}}

        for type in types:
            df = pd.concat((pd.read_csv(f + f'_{type}.txt', delimiter='\t', header=0, index_col=False)
                            for f in full_filenames))

            # https://stackoverflow.com/questions/64767166/reducing-rows-in-pandas-dataframe-from-index
            df = (df.groupby((df.index == 0).cumsum()).agg(list)
                  .map(lambda x: np.nan if np.isnan(np.array(x)).all() else np.array(x)))

            # Averaging x and y-values and 'casting' them to amplitude and phase:
            # df['avg_idx'] = df['/dev6832/demods/0/harmonic'].apply(unique_idx)

            # freq = df.apply(lambda row: avg_array(row['f'], row['avg_idx']), axis=1)
            # Z = df.apply(lambda row: avg_array(row['x']+1j*row['y'], row['avg_idx']), axis=1)

            Z = df['x'] + 1j * df['y']
            R = Z.apply(np.abs)
            P = Z.apply(np.angle)

            #
            # # Insert puts the columns first
            df.insert(0, 'Z', Z)
            df.insert(0, 'P', P)
            df.insert(0, 'R', R)
            # df.insert(0, 'Frequency', freq)

            # Column names to be consistent with before
            prefix = type.split('_')
            prefix = ' '.join(word.capitalize() for word in prefix)
            df = df.add_prefix(prefix + ' ')

            types[type]['df'] = df

        df = pd.concat([types[type]['df'] for type in types], axis=1)

        df['repeats'] = df['Sample Control f'].apply(np.size)

        # Loading Temperature data
        try:
            df_temp = pd.concat((pd.read_csv(f + f'_#temperature.txt', delimiter='\t', header=0, index_col=False)
                                 for f in full_filenames))

            # https://stackoverflow.com/questions/64767166/reducing-rows-in-pandas-dataframe-from-index
            df_temp = (df_temp.groupby((df_temp.index == 0).cumsum()).agg(list)
                       .map(lambda x: np.nan if np.isnan(np.array(x)).all() else np.array(x)))

            df_temp.rename({'Time UTC': 'Temperature Time UTC'}, inplace=True)
            df = pd.concat([df, df_temp], axis=1)

        except IOError:
            print('No Temperature data found')

        df.index -= 1

        # Creating columns denoting information in parameters
        df['Filenames'] = filenames
        params = []
        for file in full_filenames:
            with open(file + '_#parameters.txt', 'r') as f:
                lines = f.read().splitlines()
                params.append({line[2:line.find(':')]: line[line.find(':') + 2:] for line in lines})

        df_params = pd.DataFrame(params).apply(pd.to_numeric, errors='ignore')

        df = pd.concat([df, df_params], axis=1)

        # Calculate the H and M values from df_row using get_HM
        def get_HM_wrapper(df_row):
            cap = df_row['capacitor']

            # phase_correction = self.phase_correction[cap] * 2 * np.pi / 360
            # phase_correction = np.mean(self.phase_correction[cap]['diff'], axis=0)

            if df_row['imp50']:
                mag_transfer = self.distortion['imp50']['Mag Transfer']
                phase_transfer = self.distortion['imp50']['Phase Transfer']
            else:
                mag_transfer = self.distortion['HiZ']['Mag Transfer']
                phase_transfer = self.distortion['HiZ']['Phase Transfer']

            Hv, ϕv, M, ϕ = get_coeff(df_row, mag_transfer, phase_transfer)  # , phase_correction)

            return Hv, ϕv, M, ϕ

        df['H0*'], df['Hp'], df['Mn*'], df['Mpn'] = zip(*df.apply(get_HM_wrapper, axis=1))
        self.df = df

    def apply_calibration(self, cM, cH):
        self.df['H0'] = self.df['H0*'] * cH
        self.df['Mn'] = self.df['Mn*'] * cM

    def get_HM(self, filename):

        try:
            i = np.where(self.df['Filenames'] == filename)[0][0]
        except IndexError:
            print(f'{filename} does not exist in the data!')
            raise IndexError

        H0 = self.df.loc[i]['H0']
        Hp = self.df.loc[i]['Hp']
        Mn = self.df.loc[i]['Mn']
        Mpn = self.df.loc[i]['Mpn']

        fS = self.df.loc[i]['Sample Pickup f']
        fS_C = self.df.loc[i]['Sample Control f']

        repeats = self.df.loc[i]['repeats']

        # Looping through all repeated measurements
        M = 1000  # Gridpoints
        N = int(Mpn.size / repeats)  # No. harmonics

        t = np.linspace(0, 1 / fS_C[0], M)

        H, M = np.zeros((repeats, M)), np.zeros((repeats, M))

        for j in range(repeats):
            # Constructing the time signals from Fourier series
            H[j] = H0[j] * np.sin(2 * np.pi * fS_C[j] * t + Hp[j])
            M[j] = (Mn[j * N:j * N + N] * np.sin(
                np.outer(t, 2 * np.pi * fS[j * N:j * N + N]) + Mpn[j * N:j * N + N])).sum(axis=1)

        return H, M

if __name__ == '__main__':
    test = LoopTracer('data/testing')
    # print(test.df.columns)