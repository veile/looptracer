from collection import LockInAmplifier
import pandas as pd
import os

import numpy as np
import matplotlib.pyplot as plt


# Fill out fields ---------------
parameters = {
    'path':      'data/testing3/',
    'filename':  '2024-07-11 Testing new saving setting NF12_PUR 25A',
    'current':   '25', # In Amps
    'capacitor': '200nF', #200nF, 88nF, 26nF, 15nF, or 6.2nF
    'weight':    '0.1', # In g
    'imp50': 0,
    'repeats': 10,
}
# -------------------------------

filename, path = parameters['filename'], parameters['path']

# Initialize equipment
zhinst = LockInAmplifier(imp50=parameters['imp50'])


if not os.path.exists(path):
    os.mkdir(path)


# Blank measurement
Rc, Pc, fc, Rp, Pp, fp = zhinst.retrieve_signals()

print('Press enter when sample is positioned...')
input()

for n in range(parameters['repeats']):
    print(f'Repeating {n+1} out of {parameters["repeats"]} times')
    # Sample measurement
    RcS, PcS, fcS, RpS, PpS, fpS = zhinst.retrieve_signals()

    harmonic_frequency = zhinst.freq

    # Combining the data into a pandas DataFrame that is saved
    control_coil = {
        'Blank Control Frequency': fc,
        'Blank Control R': Rc,
        'Blank Control P': Pc,
        'Sample Control Frequency': fcS,
        'Sample Control R': RcS,
        'Sample Control P': PcS,
    }

    pickup_coil = {
        'Blank Pickup Frequency': fp,
        'Blank Pickup R': Rp,
        'Blank Pickup P': Pp,
        'Sample Pickup Frequency': fpS,
        'Sample Pickup R': RpS,
        'Sample Pickup P': PpS,
    }

    df_c = pd.DataFrame({key: pd.Series(value) for key, value in control_coil.items()})
    df_p = pd.DataFrame({key: pd.Series(value) for key, value in pickup_coil.items()})

    df_c.to_csv(path+filename+f'#{n}_control.csv', mode='w')
    df_p.to_csv(path+filename+f'#{n}_pickup.csv', mode='w')

    with open(path + filename + f'#{n}_parameters.txt', 'w') as f:
        for param in parameters:
            f.write(f'# {param}: {parameters[param]}\n')


# Plotting result without any corrections------------------------------------------------------------------------------
from scipy.integrate import trapezoid, cumulative_trapezoid
def reconstruct(t, f, R, P):
    '''
    Reconstructs the voltage signal as function of time from arrays of frequency, amplitude and phase.
    mag_transfer and phase_transfer should be functions of frequency determined by the distortion.

    If no functions are inputted, the signal will not be corrected
    '''
    amplitude = np.sqrt(2) * R
    phase = P

    return (amplitude * np.sin(np.outer(t, 2 * np.pi * f) + phase)).sum(axis=1)

def reduce(f, R, P):
    '''
    This function takes in the raw values of frequency, amplitude and phase.
    All nan values are removed, and the mean values are taken for each frequency.

    Returns 3 arrays of averages values
    '''
    # Have to use cartesian coordinates to take proper mean values - consider saving X/Y instead?
    # E.g. averaging -180° and 180°, should NOT result in 0.
    Z = R * np.exp(1j * P)
    X = Z.real
    Y = Z.imag

    # Finding all the frequencies by looking at the difference.
    # First value will always be the the first frequency, so it is appended
    idx = np.append([0], np.where(np.diff(f) > 100)[0] + 1)

    # Probably this can be done more efficiently but it does the trick
    f_sum = []
    X_sum = []
    Y_sum = []
    for i in range(len(idx)):
        if i == len(idx) - 1:
            f_sum.append(np.mean(f[idx[i]:]))
            X_sum.append(np.mean(X[idx[i]:]))
            Y_sum.append(np.mean(Y[idx[i]:]))

        else:
            f_sum.append(np.mean(f[idx[i]:idx[i + 1]]))
            X_sum.append(np.mean(X[idx[i]:idx[i + 1]]))
            Y_sum.append(np.mean(Y[idx[i]:idx[i + 1]]))

    f = np.array(f_sum)
    X = np.array(X_sum)
    Y = np.array(Y_sum)

    Z = X + 1j * Y
    R = np.abs(Z)
    P = np.angle(Z)

    return f, R, P

# Pickup signal
f, R, P = reduce(df_p['Blank Pickup Frequency'], df_p['Blank Pickup R'], df_p['Blank Pickup P'])
fS, RS, PS = reduce(df_p['Sample Pickup Frequency'], df_p['Sample Pickup R'], df_p['Sample Pickup P'])

# # Control signal
f_C, R_C, P_C = reduce(df_c['Blank Control Frequency'], df_c['Blank Control R'], df_c['Blank Control P'])
fS_C, RS_C, PS_C = reduce(df_c['Sample Control Frequency'], df_c['Sample Control R'], df_c['Sample Control P'])

t = np.linspace(0, 1 / f[0], 1000)

VS = reconstruct(t, fS, RS, PS)
V = reconstruct(t, f, R)

VS_C = reconstruct(t, fS_C, RS_C, PS_C)
V_C = reconstruct(t, f_C, R_C, P_C)

# # Integration
m = - cumulative_trapezoid(VS, t, initial=0) + cumulative_trapezoid(V, t, initial=0)
H = cumulative_trapezoid(V_C, t, initial=0)

integral_m = trapezoid(m, t)
integral_H = trapezoid(H, t)

dc_m = integral_m * f[0]
dc_H = integral_H * f[0]

m = m - dc_m
H = H - dc_H

fig, ax = plt.subplots()

ax.plot(H, m)
plt.show()