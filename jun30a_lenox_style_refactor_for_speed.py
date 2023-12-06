# Capturing the properties of the circuit formed by the pick-up system (coil, wires, connectors, etc. up until the input of the lock-in-amp).
# This is inspired by the work by Lenox et al in https://doi.org/10.1109/LMAG.2017.2768521
#
# The background noise was different across multiple days (depending on what other equipment is running in our lab? Or other labs?)
# I thus ended up doing two different things on different days:
# a) there was transients on the pick-up-coil signal with fundamental time period of around 2 us and peak of 20 mV
#    the transient was only visible once every few seconds.
#    In this case -> use outlier detection
#
# b) there is periodic noise/transients in rapid succession. -> use "blank run" and subtraction for noise cancellation
#
# To actually write the calibration data to .csv file, run the distortion_cal-data_to_csv.py script after this one

import time
import numpy as np
import matplotlib.pyplot as plt
import zhinst.core
from numpy import ndarray

def sweep_multipoint(frequency_sweep: ndarray, recording_time_s: float, points_per_freq: int, verbose: bool= False, filter_outliers: bool = True):
    i_x_result = np.array([])
    i_y_result = np.array([])
    v_x_result = np.array([])
    v_y_result = np.array([])

    for freq in frequency_sweep:
        # Initialize/clear buffer
        i_x = np.array([])
        i_y = np.array([])
        v_x = np.array([])
        v_y = np.array([])

        # Set and print new frequency
        daq.setDouble('/dev6832/oscs/0/freq', freq)
        daq.sync()
        print(f'\n {freq:.0f} Hz')
        time.sleep(waiting_time_s)

        # Get current data and append to buffer
        daq.setInt('/dev6832/demods/0/adcselect', 1)
        daq.sync()
        daq.subscribe('/dev6832/demods/0/sample')
        time.sleep(waiting_time_s)
        for i in range(points_per_freq):
            # time.sleep(0.2)
            data = daq.poll(recording_time_s=recording_time_s, timeout_ms=200, flags=1, flat=True)
            if '/dev6832/demods/0/sample' in data:
                # access the demodulator data:
                i_x = np.append(i_x, np.mean(data['/dev6832/demods/0/sample']['x']))
                i_y = np.append(i_y, np.mean(data['/dev6832/demods/0/sample']['y']))

                # Print current values, if verbose flag is true
                if verbose:
                    # print i_x, i_y
                    print(f'{i_x[-1]*1000:.3f} mA, {i_y[-1]*1000:.3f} mA')
        # Get voltage data and append to buffer
        daq.setInt('/dev6832/demods/0/adcselect', 0)
        # daq.setInt('/dev6832/demods/0/adcselect', 8)
        daq.sync()
        daq.subscribe('/dev6832/demods/0/sample')
        time.sleep(waiting_time_s)
        for i in range(points_per_freq):
            # time.sleep(0.2)
            data = daq.poll(recording_time_s, 200, 1, True)
            if '/dev6832/demods/0/sample' in data:
                # access the demodulator data:
                v_x = np.append(v_x, np.mean(data['/dev6832/demods/0/sample']['x']))
                v_y = np.append(v_y, np.mean(data['/dev6832/demods/0/sample']['y']))
                # Print current values, if verbose flag is true
                if verbose:
                    # print v_x, v_y
                    print(f'{v_x[-1] :.7f} , {v_y[-1] :.7f}')

        # detect and remove outliers:
        if filter_outliers:
            i_mag, i_theta_deg, v_meas_mag, v_meas_theta_deg = convert_cartesian_to_mag_and_phase(i_x, i_y, v_x, v_y)   # want to remove outliers based on magnitude
            mask = np.abs(v_meas_mag - np.mean(v_meas_mag)) < 1 * np.std(v_meas_mag)
            if np.sum(mask) > 0:
                print(f'{np.sum(~mask)} outliers detected out of {len(mask)} points')

        else:
            # mask that includes all
            mask = np.ones(len(v_x), dtype=bool)

        v_x_no_outliers = v_x[mask]
        v_y_no_outliers = v_y[mask]
        i_x_no_outliers = i_x[mask]
        i_y_no_outliers = i_y[mask]

        # average and append to result arrays: these only contain one value per frequency
        i_x_result = np.append(i_x_result, np.mean(i_x_no_outliers))
        i_y_result = np.append(i_y_result, np.mean(i_y_no_outliers))
        v_x_result = np.append(v_x_result, np.mean(v_x_no_outliers))
        v_y_result = np.append(v_y_result, np.mean(v_y_no_outliers))


    return i_x_result, i_y_result, v_x_result, v_y_result


def convert_cartesian_to_mag_and_phase(i_x: ndarray, i_y: ndarray, v_x: ndarray, v_y: ndarray, flip_voltage_phase: bool = False):
    # Calculating magnitudes and phases from cartesian form
    i_mag = np.sqrt(i_x ** 2 + i_y ** 2)
    i_theta_rad = np.arctan2(i_y, i_x)
    i_theta_deg = np.multiply(i_theta_rad, 180 / np.pi)
    v_meas_mag = np.sqrt(v_x ** 2 + v_y ** 2)
    v_meas_theta_rad = np.arctan2(v_y, v_x)

    if flip_voltage_phase:
        v_meas_theta_deg = np.multiply(v_meas_theta_rad, 180 / np.pi) +180
    else:
        v_meas_theta_deg = np.multiply(v_meas_theta_rad, 180 / np.pi)

    # return
    return i_mag, i_theta_deg, v_meas_mag, v_meas_theta_deg


# Set voltage to apply to excitation coil via lock-ins signal output
V_out = 0.8

# Set frequency range for sweep
freq_sweep = np.geomspace(1e5, 1e6, 50)
n_points_per_freq = 10  # repeat measurement at each frequency this many times
omega_sweep = 2*np.pi * freq_sweep

# Set averaging window for polling data from lock-in amplifier
averaging_window_s = 0.001

# Waiting time between setting new frequency and starting measurement
waiting_time_s = 0.2

# Connecting to the lock-in amplifier
# daq = zhinst.core.ziDAQServer('mf-dev6832', 8004, 6)  # This was how Thomas could connect.
# I instead needed:
dev = 'dev6832'
d = zhinst.core.ziDiscovery()
props = d.get(d.find(dev))
print('GUI can be reached through entering serveradress', props['serveraddress'], ' into adressfield of webbrowser.')
daq = zhinst.core.ziDAQServer(props['serveraddress'], 8004, 6)

# Set voltage measurement input to 50 Ohms (less noise this way)
daq.setInt('/dev6832/sigins/0/imp50', 0)

# Use internal oscillator as reference
daq.setInt('/dev6832/extrefs/0/enable', 0)

# Set Data Transfer Rate
daq.setInt('/dev6832/demods/0/rate', 1674)

# Sweep with output activated: capture actual signals of interest
daq.setDouble('/dev6832/sigouts/0/amplitudes/1', V_out)
daq.setInt('/dev6832/sigouts/0/on', 1)
time.sleep(3)

I_x_raw, I_y_raw, V_x_raw, V_y_raw = sweep_multipoint(freq_sweep, averaging_window_s, n_points_per_freq, False, True)

# ------- Uncomment this for using noise cancellation via blank run
#
# # Sweep with output deactivated: capture noise to subtract later
# daq.setInt('/dev6832/sigouts/0/on', 0)
# time.sleep(3)
# I_x_noise, I_y_noise, V_x_noise, V_y_noise = sweep_multipoint(freq_sweep, averaging_window_s, n_points_per_freq, False, False)
#
# # Subtracting noise
# I_x = I_x_raw - I_x_noise
# I_y = I_y_raw - I_y_noise
# V_x = V_x_raw - V_x_noise
# V_y = V_y_raw - V_y_noise

# ----------------------------------------------------------------

# alternative: proceed without subtracting noise/blank run
I_x = I_x_raw
I_y = I_y_raw
V_x = V_x_raw
V_y = V_y_raw



# Calculating magnitudes and phases from cartesian form
I_mag, I_theta_deg, V_meas_mag, V_meas_theta_deg = convert_cartesian_to_mag_and_phase(I_x, I_y, V_x, V_y, True)


# voltage induced in pick-up coil is proportional to frequency * I_mag, with an unknown constant -> au means arbitrary unit
V_ind_mag_au = np.multiply(omega_sweep, I_mag)
# What we are actually interested in: how does expected induced voltage relate to the voltage we can measure?
transfer_mag = np.divide(V_meas_mag,V_ind_mag_au)

# Calculating transfer phase: phase of voltage measured at pick-up coil BNC relative to excitation current
# -90 because ideally we'd have +90 relative to the current and we want to just subtract this value later when using it for correction
transfer_theta_deg = V_meas_theta_deg - I_theta_deg - 90


fig, ax = plt.subplots()

ax.semilogx(freq_sweep, transfer_mag, 'C0s', label='Magnitude Transfer')
ax.set_ylabel('Magnitude transfer')

ax2 = ax.twinx()

ax2.semilogx(freq_sweep, transfer_theta_deg, 'C1o', label='Phase Shift')
ax2.set_ylabel('Phase transfer [°]')

ax.legend()
fig.tight_layout()
plt.show()

arrays_to_save = {'I_mag': I_mag, 'I_theta_deg': I_theta_deg, 'transfer_mag': transfer_mag, 'transfer_theta_deg': transfer_theta_deg}

# # Plot
# fig1, ax1 = plt.subplots()
# ax1.semilogx(freq_sweep, transfer_mag, 's')
# ax1.set_ylim(bottom=0)
# plt.ylabel('V_measured/V_induced in a.u.')
# plt.title('V_out_MFLI = ' + str(V_out) + ' V')
# plt.show()
#
# fig2, ax2 = plt.subplots()
# lns2=ax2.semilogx(freq_sweep, I_theta_deg, '^', label="excitation current phase")
# plt.ylabel('Current phase in deg')
# plt.ylim(top=90, bottom=-100)
#
# ax3 = ax2.twinx()
# lns3=ax3.semilogx(freq_sweep, transfer_theta_deg, 's', label="measured voltage phase")
# plt.ylabel('\phi_{PUC} - \phi_{i_excitation}, in deg')
# plt.ylim(top=90, bottom=-100)
#
# lns = lns2+lns3
# labs = [l.get_label() for l in lns]
# plt.legend(lns, labs, loc=0)
#
# plt.show()
#
# fig3, ax4 = plt.subplots()
# ax4.semilogx(freq_sweep, I_mag, '^', label="excitation current magnitude")
# plt.ylabel('excitation current magnitude in A')
# plt.title('V_out_MFLI = ' + str(V_out) + ' V,  n_points_per_freq = ' + str(n_points_per_freq))
#
# plt.show()
#
# # plotting the voltage transfer and phase correction for the pick-up coil
# fig4, ax5 = plt.subplots()
# ax5.semilogx(freq_sweep, transfer_mag, 's', label="voltage transfer")
# plt.ylabel('V_measured/V_induced in a.u.')
# plt.title('V_out_MFLI = ' + str(V_out) + ' V,  n_points_per_freq = ' + str(n_points_per_freq))
#
# ax6 = ax5.twinx()
# ax6.semilogx(freq_sweep, transfer_theta_deg, '^', label="phase error")
# plt.ylabel('\phi_{PUC} - \phi_{i_excitation}, in deg')
# plt.ylim(top=20, bottom=-20)
# plt.show()