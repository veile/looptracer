from collection import LockInAmplifier
from processing import reconstruct
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt

print("Please write filename (without any extension)")
filename = input()

# Initialize equipment
zhinst = LockInAmplifier()

with open(filename+'.csv', 'w') as f:
    f.write('Some settings')
    settings = zhinst.get_settings()
    for key, item in settings.items():
        i = key.rfind('/')+1
        f.write(f"# {key}\t{item['value'][0]}\n")
        # print(key[i:], item['value'])

# # print('''Choose Capacitance:\n1. 6.2 nF\n2. 15 nF\n3. 26 nF\n4. 88 nF\n5. 200 nF\n''')
# # cap_input = input()
# #
# # cap = {'1': '6.2 nF', '2': '15 nF', '3': '26 nF', '4': '88 nF', '5': '200 nF'}[cap_input]
# # filename = f'FieldCal {cap}.txt'
# # zhinst.calibrate_field('data/'+filename, 'COM6', capacitance=cap)
#
# # Blank measurement
# Rc, Pc, fc, Rp, Pp, fp = zhinst.retrieve_signals()
#
# print('Press enter when sample is positioned...')
# input()
#
# RcS, PcS, fcS, RpS, PpS, fpS = zhinst.retrieve_signals()
#
# harmonic_frequency = zhinst.freq
#
# # Combining the data into a pandas DataFrame that is saved
# data = {
#     'Blank Control Frequency': fc,
#     'Blank Control R': Rc,
#     'Blank Control P': Pc,
#     'Blank Pickup Frequency': fp,
#     'Blank Pickup R': Rp,
#     'Blank Pickup P': Pp,
#     'Sample Control Frequency': fcS,
#     'Sample Control R': RcS,
#     'Sample Control P': PcS,
#     'Sample Pickup Frequency': fpS,
#     'Sample Pickup R': RpS,
#     'Sample Pickup P': PpS,
# }
#
# df = pd.DataFrame({key: pd.Series(value) for key, value in data.items()})
# df.to_csv('data/'+filename+'.csv', mode='a')
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