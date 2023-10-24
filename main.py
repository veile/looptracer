from collection import LockInAmplifier
from processing import CoilSignals, HysCurve
import matplotlib.pyplot as plt

print("Please write filename (without any extension)")
filename = input()

# Initialize equipment
zhinst = LockInAmplifier()

# print('''Choose Capacitance:\n1. 6.2 nF\n2. 15 nF\n3. 26 nF\n4. 88 nF\n5. 200 nF\n''')
# cap_input = input()
#
# cap = {'1': '6.2 nF', '2': '15 nF', '3': '26 nF', '4': '88 nF', '5': '200 nF'}[cap_input]
# filename = f'FieldCal {cap}.txt'
# zhinst.calibrate_field('data/'+filename, 'COM6', capacitance=cap)


# zhinst.daq.setInt(f'/dev6832/demods/0/harmonic', 1)
# zhinst.daq.setInt('/dev6832/demods/0/phaseadjust', 1)

# Blank measurement
Rc, Pc, fc, Rp, Pp, fp = zhinst.retrieve_signals()

# Adjusting phase shift between pick-up coil and control coil
# shift = Pp[0] - Pc
# Pp[0] = Pc

# print(f"Control phase before reconstuction: {Pc}")
# print(f"Pickup phase before reconstuction: {Pp[0]}")

Vc = zhinst._reconstruct(Rc, Pc, [fc], control_coil=True)
Vp = -zhinst._reconstruct(Rp, Pp, fp)
blank = CoilSignals(zhinst.t, Vp, Vc, zhinst.freq)

# plt.plot(tc, Vp)
# plt.plot(tc, Vc)
# plt.show()


print('Press enter when sample is positioned...')
input()

RcS, PcS, fcS, RpS, PpS, fpS = zhinst.retrieve_signals()

# PpS[0] = PpS[0]-shift

VcS = zhinst._reconstruct(RcS, PcS, [fcS], control_coil=True)
VpS = -zhinst._reconstruct(RpS, PpS, fpS)
sample = CoilSignals(zhinst.t, VpS, VcS, zhinst.freq)

freq = zhinst.freq

header = "Blank Time\tBlank Pickup\tBlank Control\tSample Time\tSample Pickup\tSample Control\n"
with open(f'data/{filename}.txt', 'w') as f:
    f.write(f'# Frequency\t{freq}\n')
    f.write(header)
    for i in range(blank.t.size):
        row = f'{blank.t[i]}\t{blank.Vp[i]}\t{blank.Vc[i]}\t{sample.t[i]}\t{sample.Vp[i]}\t{sample.Vc[i]}\n'
        f.write(row)

fig, axs = plt.subplots(3, 1)
ax, ax2, ax3 = axs

H = HysCurve(sample, blank, 1, 1)

ax.plot(H.X, H.Y)

ax2twin = ax2.twinx()
import numpy as np
t_plot = np.linspace(0, 8/zhinst.freq, 8000)
ax2.plot(t_plot, np.tile(VpS, 8), label='Pickup Sample', c='C0')
ax2twin.plot(t_plot, np.tile(VcS, 8), label='Field Sample', c='C1')
ax2.plot(t_plot, np.tile(Vp,8), label='Pickup Blank', c='C2')
ax2twin.plot(t_plot, np.tile(Vc, 8), label='Field Blank', c='C3')

hnd1, lbl1 = ax2.get_legend_handles_labels()
hnd2, lbl2 = ax2twin.get_legend_handles_labels()

hnd = hnd1+hnd2
lbl = lbl1+lbl2

ax2.legend(hnd, lbl, loc='upper left', bbox_to_anchor=(1,1))

ax3.plot(t_plot, np.tile(VpS-Vp, 8))

for a in axs[1:]:
    a.set_xlim(0, 8/freq)

plt.show()