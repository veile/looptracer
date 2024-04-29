import numpy as np
from collection import LockInAmplifier
import time
import matplotlib.pyplot as plt

filename = "2024-04-27 distortion imp50 50pts.txt"

zhinst = LockInAmplifier(imp50=0)

f, I, V = zhinst.distortion_corection(50)


# The expected voltage is equal to frequency, current and some coil property constant.
# The constant is not important as we calibrate the system later.
Vexp = f*np.abs(I)

# Magnitude transfer denotes the attenuation/rise of the true voltage due to the pick-up coils.
# This constant needs to be multiplied onto the measured voltage
mag_transfer = Vexp / np.abs(V)

# Phase transfer denotes the phase shift imposed by the pick-up system
# The phase shift needs to be added onto the measured phase.
# A coil has the voltage V = L dI/dt, so the expected voltage is 90 degree shifted from the current
Pexp = np.angle(I*np.exp(1j*np.pi/2))

# This is to correctly add angles
# pi is added to get the phase in range of 0 - 2pi to use modulus and then subtract eh pi again.
phase_transfer = (Pexp - np.angle(V)+np.pi) % (2*np.pi) - np.pi


# Plotting the results
fig, ax = plt.subplots()

ax.semilogx(f, mag_transfer, 'C0s', label='Magnitude Transfer')
ax.set_ylabel('Magnitude transfer')

ax2 = ax.twinx()

ax2.semilogx(f, phase_transfer*180/np.pi, 'C1o', label='Phase Shift')
ax2.set_ylabel('Phase transfer [°]')

ax.legend()
ax2.legend()
fig.tight_layout()
plt.show()

# arrays_to_save = {'f': f, 'I': I, 'V': V}s
np.savetxt(filename, (f, I, V))