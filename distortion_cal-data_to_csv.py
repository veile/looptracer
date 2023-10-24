
import csv
# Create a CSV file and write the data
filename = "calib_03_07_2023_final_hi-z.csv"
with open(filename, mode='w', newline='') as file:
    writer = csv.writer(file)

    # Write file header
    writer.writerows([
        ["Transfer Magnitude is: a value proportional to the ratio between measured and expected voltage (pick-up coil)."],
        ["The expected value is calculated from the excitation current and frequency."],
        ["{V_ind_measured / c*V_ind_ideal} = {V_ind_measured / I_excitation * f} where c is an unknown constant."],
        ["To use, divide the measured voltage by this."],
        ["The unknown constant can stay unkown, when in a later step, the measured voltage is scaled again, based on calibration using the VSM."],
        [],
        ["Transfer Phase is: the deviation from the ideal behaviour,"],
        ["i.e. if it is 0, that means the PUC-voltage had a +90deg phase shift relative to the excitation current."],
        ["That would be the case for the pick-up coil acting as an ideal inductor"],
        ["and the circuit formed by pick-up, connection wires, connectors, BNC-cable, lock-in input impedance"],
        ["not distorting the signal at all."],
        ["To be used for correcting measurement data by subtracting this value from the measured phase."]])


    # Write the data
    writer.writerow(["Frequency", "Transfer Magnitude", "Transfer Phase in degrees"])
    for freq, mag, phase in zip(freq_sweep, transfer_mag, transfer_theta_deg):
        writer.writerow([freq, mag, phase])
