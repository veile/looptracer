from collection import LockInAmplifier
from zhinst.utils import save_settings
from processing import reconstruct
import pandas as pd
import os

import numpy as np
import matplotlib.pyplot as plt


# Fill out fields ---------------
parameters = {
    'path':      'data/testing/',
    'filename':  '2024-07-09 Testing new saving settings NF 10A',
    'current':   '10', # In Amps
    'capacitor': '200nF', #200nF, 88nF, 26nF, 15nF, or 6.2nF
    'weight':    '0.1', # In g
    'imp50': 0,
}
# -------------------------------

filename, path = parameters['filename'], parameters['path']

# Initialize equipment
zhinst = LockInAmplifier(imp50=parameters['imp50'])


if not os.path.exists(path):
    os.mkdir(path)

#save_settings(zhinst.daq, 'dev6832', path+filename+'_settings')

with open(path+filename+'_parameters.txt', 'w') as f:
    for param in parameters:
        f.write(f'# {param}: {parameters[param]}\n')

# Blank measurement
Rc, Pc, fc, Rp, Pp, fp = zhinst.retrieve_signals()

print('Press enter when sample is positioned...')
input()

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

df_c.to_csv(path+filename+'_control.csv', mode='a')
df_p.to_csv(path+filename+'_pickup.csv', mode='a')

#
#
#
# VpS = reconstruct(df['Sample Pickup Frequency'].values, df['Sample Pickup R'].values,
#                   df['Sample Pickup P'].values, lambda f: 1, lambda f:0)
# Vp = reconstruct(df['Blank Pickup Frequency'].values, df['Blank Pickup R'].values,
#                  df['Blank Pickup P'].values, lambda f: 1, lambda f:0)
# VcS = reconstruct(df['Sample Control Frequency'].values, df['Sample Control R'].values,
#                   df['Sample Control P'].values, lambda f: 1, lambda f:0, control_coil=True)
# Vc = reconstruct(df['Blank Control Frequency'].values, df['Blank Control R'].values,
#                  df['Blank Control P'].values, lambda f: 1, lambda f:0, control_coil=True)
#
# t_plot = np.linspace(0, 8/zhinst.freq, 8000)
# # Blank compensation
# m = -VpS(t_plot) + Vp(t_plot)
# H = VcS(t_plot)
#
# # Offset Correction
# m = m - np.mean(m)
# H = H - np.mean(H)
#
# fig, axs = plt.subplots(3, 1)
# ax, ax2, ax3 = axs
#
# ax.plot(H, m)
#
# ax2twin = ax2.twinx()
#
# ax2.plot(t_plot, VpS(t_plot), label='Pickup Sample', c='C0')
# ax2twin.plot(t_plot, VcS(t_plot), label='Field Sample', c='C1')
# ax2.plot(t_plot, Vp(t_plot), label='Pickup Blank', c='C2')
# ax2twin.plot(t_plot, Vc(t_plot), label='Field Blank', c='C3')
#
# hnd1, lbl1 = ax2.get_legend_handles_labels()
# hnd2, lbl2 = ax2twin.get_legend_handles_labels()
#
# hnd = hnd1+hnd2
# lbl = lbl1+lbl2
#
# ax2.legend(hnd, lbl, loc='upper left', bbox_to_anchor=(1,1))
#
# ax3.plot(t_plot, VpS(t_plot) - Vp(t_plot))
#
# for a in axs[1:]:
#     a.set_xlim(0, 8/zhinst.freq)
#
# plt.show()