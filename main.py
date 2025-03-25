from collection import LockInAmplifier
from processing import LoopTracer
from devices import PowerSupply

import time
import os
import glob
import matplotlib.pyplot as plt

# From own measurements of current in the 18T external coil.
coilconstant = {'200nF': 1.69, '88nF': 1.65, '26nF': 1.57, '15nF': 1.47, '6.2nF': 1.20}  # mT/A
# From Magnetherm
# coilconstant = {'200nF': 1.65, '88nF': 1.65, '26nF': 1.58, '15nF': 1.52, '6.2nF': 1.36}  # mT/A

maxcurrent = {'200nF': 28, '88nF': 23, '26nF': 20, '15nF': 17, '6.2nF': 13}  # A

# Fill out fields --------------------------------------------------------------------
parameters = {
    'path':      'data/2025-03-05 NF12 hBN_b2/',
    'filename':  '2025-03-05 15nF 18.9mT NF12 hBN_b2 43mg',
    #'filename': '2025-03-05 15nF 18.9mT Dy2O3 #1',
    'field':   18.9,  # In mT
    'capacitor': '15nF',  # 200nF, 88nF, 26nF, 15nF, or 6.2nF
    'weight':    43,  #
    'imp50': 0,
}
# ------------------------------------------------------------------------------------
parameters['current'] = parameters['field'] / coilconstant[parameters['capacitor']]
if parameters['current'] > maxcurrent[parameters['capacitor']]:
    raise Exception('Current value is too high!')

filename, path = parameters['filename'], parameters['path']

# Initialize equipment
psu = PowerSupply('COM6')
zhinst = LockInAmplifier(imp50=parameters['imp50'])

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

# Start of measurement procedure ---------------------------------------------------------------------------------------
print('Insert blank vial and press Enter...')  # 1
input()


psu.set(45, parameters['current'])  # 2 (Thermalizing the system)
psu.set_output('ON')
time.sleep(5)

zhinst.retrieve_vc(full_filename+'_blank_control.txt')  # 3 (blank measurement)
zhinst.retrieve_vp(full_filename+'_blank_pickup.txt')

#psu.set_output('OFF')
print('Insert sample vial and press Enter...')  # 4
input()

#psu.set(45, parameters['current'])  # 5 (Turning on field and measuring on sample)
#psu.set_output('ON')
#time.sleep(1) # To make sure field is on

zhinst.retrieve_vc(full_filename + f'_sample_control.txt') # 6 Measure sample
zhinst.retrieve_vp(full_filename + f'_sample_pickup.txt')

#psu.set_output('OFF')  # 7 Finished

# Plotting result without any phase or distortion corrections----------------------------------------------------------
import numpy as np
lt = LoopTracer(path)
lt.apply_calibration(cM = 1.928E-04, cH = 1.251e10)
i = np.where(lt.df['Filenames'] == filename)[0][0]
H, m = lt.get_HM(i)

fig, ax = plt.subplots()

ax.plot(H[0]*4*np.pi*1e-7*1e3, m[0])

ax.set_xlabel('Applied Field [mT]')
ax.set_ylabel('Moment [Am2]')

plt.show()
