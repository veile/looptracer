    # -*- coding: utf-8 -*-
"""
Created on Wed Sep  9 12:32:52 2020

@author: Veile
"""
import serial
import time
import random
import sys
from osensapy import osensapy

class WrongDeviceError(Exception):
    """Base class for wrong device"""


class fiber:
    '''
    id = 247 single channel transmitter
    id = 40  triple channel transmitter
    '''

    def __init__(self, port, id=40):
        self.transmitter = osensapy.Transmitter(port, id, baudrate=115200)

    def __len__(self):
        return 3

    def get_T(self):
        return [reading[1] for reading in self.transmitter.fast_batch(3)]

    def reinitialize(self):
        port = self.transmitter.modbus.serial.port
        self.transmitter.close()
        self.transmitter = osensapy.Transmitter(port, 247, baudrate=115200)


class PowerSupply:
    endchar = "\r\n"

    def __init__(self, port, baudrate=9600):

        self.ser = serial.Serial(port=port,
                                 baudrate=baudrate)

        self.set_default()

    def comm(self, cmd):
        cmd = cmd + self.endchar
        self.ser.write(cmd.encode('utf-8'))

        time.sleep(.07)

        reply = self.ser.read(self.ser.inWaiting()).decode('utf-8', errors='ignore')
        if reply == '':
            return self.error_status().strip(self.endchar)
        else:
            return reply.strip(self.endchar)

    def error_status(self):
        return self.comm('EER?')

    def get_id(self):
        return self.comm('*IDN?')

    def get_V(self):
        return self.comm('V1O?')

    def set_V(self, V):
        # Checks if input is allowed
        if not 0 <= V <= 60:
            raise ValueError("Voltage is not within required range 0-60V")
        return self.comm('V1 ' + str(V))

    def get_I(self):
        return self.comm('I1O?')

    def set_I(self, I):
        # Checks if input is allowed
        if not 0 <= I <= 30:
            raise ValueError("Current is not within required range 0-20A")
        return self.comm('I1 ' + str(I))

    def set(self, V, I):
        self.set_V(V)
        self.set_I(I)

    def get_output(self):
        cmd = 'OP1?' + self.endchar
        self.ser.write(cmd.encode('utf-8'))
        time.sleep(self.wait)
        # Reads return message
        out = ''
        while self.ser.in_waiting > 0:
            out += self.ser.readline().decode('utf-8')
        return out

    def set_output(self, state):
        modes = {'OFF': 0,
                 'ON': 1}
        if isinstance(state, str):
            s = state.upper()
            if s not in ['OFF', 'ON']:
                raise NameError("%s is not a valid output mode!" %s)
            mode = modes[s]
        else:
            if state not in [0, 1]:
                raise NameError("%s is not a valid input" %str(state))
            mode = state

        return self.comm('OP1 ' + str(mode))

    def set_default(self):
        self.set(0, 0)
        self.set_output('OFF')

    def status(self):
        V = self.get_V()
        I = self.get_I()
        OP = self.get_output()

        status = V+I+OP
        return status