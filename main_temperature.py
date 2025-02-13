from collection import LockInAmplifier, Magnetherm
# from processing import LoopTracer

import os
import glob
import time
import threading
# import matplotlib.pyplot as plt

# From own measurements of current in the 18T external coil.
coilconstant = {'200nF': 1.69, '88nF': 1.65, '26nF': 1.57, '15nF': 1.47, '6.2nF': 1.20}  # mT/A
# From Magnetherm
# coilconstant = {'200nF': 1.65, '88nF': 1.65, '26nF': 1.58, '15nF': 1.52, '6.2nF': 1.36}  # mT/A

maxcurrent = {'200nF': 28, '88nF': 23, '26nF': 20, '15nF': 17.5, '6.2nF': 13}  # A

# Fill out fields --------------------------------------------------------------------
parameters = {
#   'path':      'data/2024-12-11 NF12 #3/',
    'path':      'data/2024-12-10 Dy2O3 #1/',
#    'filename':  '2024-12-13 NF12#3 26nF 30mT',
    'filename':  '2024-12-13 Dy2O3#1 15nF 25mT',
    'field':   25,  # In mT
    'capacitor': '15nF',  # 200nF, 88nF, 26nF, 15nF, or 6.2nF
    'volume-ml':    1,
    'weight': (4.0246-3.0176), #in g
    'sample-height': 16, # mm
    'imp50': 0,
    'spacer-mm': 7,
}
# ------------------------------------------------------------------------------------
parameters['current'] = parameters['field'] / coilconstant[parameters['capacitor']]
if parameters['current'] > maxcurrent[parameters['capacitor']]:
    raise Exception('Current value is too high!')

filename, path = parameters['filename'], parameters['path']

m = Magnetherm('COM7', 'COM6')

if not os.path.exists(path):
    os.mkdir(path)

full_filename = os.path.join(path, filename)
if os.path.isfile(full_filename+'_#parameters.txt'):
    print('File already exists!')
    print('Press enter to overwrite! (Ctrl+C to interrupt)')
    input()

    list(map(os.remove, glob.glob(full_filename+'*')))

with open(full_filename+'_#parameters.txt', 'w') as f:
    for param in parameters:
        f.write(f'# {param}: {parameters[param]}\n')

# Initializing the PSU and thread to save temperature measurements
thread_magnetherm = threading.Thread(target=m.run, args=(full_filename+'_#temperature.txt', .5))


# Start of measurement procedure ---------------------------------------------------------------------------------------
print('Insert blank vial and press Enter...')  # 1
input()

m.psu.set(45, parameters['current'])  # 2 (Thermalizing the system)
m.psu.set_output('ON')
time.sleep(60) # 5 min was excessive looking at calibration data

# Initialize lockin amplifier
zhinst = LockInAmplifier(imp50=parameters['imp50'])

zhinst.retrieve_vc(full_filename+'_blank_control.txt')  # 3 (blank measurement)
zhinst.retrieve_vp(full_filename+'_blank_pickup.txt')

m.psu.set_output('OFF')
print('Insert sample vial and press Enter...')  # 4
input()

thread_magnetherm.start()  # 5 (Starting calorimetric measurement - getting background temperature)
time.sleep(10)  # Should maybe be higher

m.psu.set(45, parameters['current'])  # 6 (Turning on field and measuring on sample)
m.psu.set_output('ON')
time.sleep(1) # To make sure field is on

keep_going = True
def key_capture_thread():
    global keep_going
    input()
    keep_going = False


def measure_sample():
    threading.Thread(target=key_capture_thread, daemon=True).start()

    N = 0
    while keep_going:
        zhinst.retrieve_vc(full_filename + f'_sample_control.txt')
        zhinst.retrieve_vp(full_filename + f'_sample_pickup.txt')
        print(f'{N+1} Loops measured')
        N += 1
print('Press Enter to stop measurement...')
measure_sample()

m.psu.set_output('OFF')  # 7 (Measure cooling curve)
#time.sleep(30)
time.sleep(1)
m.stop()
thread_magnetherm.join()

# # Blank measurement at end
# print('Insert blank vial and press enter ...')
# input()
# m.psu.set(45, parameters['current'])
# m.psu.set_output('ON')
# time.sleep(60)
# zhinst.retrieve_vc(full_filename+'_blank_control.txt')  # 3 (blank measurement)
# zhinst.retrieve_vp(full_filename+'_blank_pickup.txt')
# m.psu.set_output('OFF')


print('Measurement finished')
# # Plotting results ---------------------------------------------------------------------------------------------------
# lt = LoopTracer(path)
# lt.apply_calibration(1e8, 1e4)
# H, m = lt.get_HM(filename)
#
# fig, ax = plt.subplots()
#
# ax.plot(H, m)
# plt.show()
