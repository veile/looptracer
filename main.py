from collection import LockInAmplifier
from processing import LoopTracer

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
    'path':      'data/testing/',
    'filename':  '2024-12-09 NF12',
    'field':   35,  # In mT
    'capacitor': '88nF',  # 200nF, 88nF, 26nF, 15nF, or 6.2nF
    'weight':    0,  # In g
    'imp50': 0,
}
# ------------------------------------------------------------------------------------
parameters['current'] = parameters['field'] / coilconstant[parameters['capacitor']]
if parameters['current'] > maxcurrent[parameters['capacitor']]:
    raise Exception('Current value is too high!')

filename, path = parameters['filename'], parameters['path']

# Initialize equipment
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

# Blank measurement
zhinst.retrieve_vc(full_filename+'_blank_control.txt')
zhinst.retrieve_vp(full_filename+'_blank_pickup.txt')

print('Press enter when sample is positioned...')
input()

# Sample measurement
zhinst.retrieve_vc(full_filename+'_sample_control.txt')
zhinst.retrieve_vp(full_filename+'_sample_pickup.txt')


# Plotting result without any corrections------------------------------------------------------------------------------
lt = LoopTracer(path)
lt.apply_calibration(1e8, 1e4)
H, m = lt.get_HM(filename)

fig, ax = plt.subplots()

ax.plot(H, m)
plt.show()
