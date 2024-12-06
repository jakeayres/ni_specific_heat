import nidaqmx
from loguru import logger
from nidaqmx.constants import (AcquisitionType, CountDirection, Edge,
    READ_ALL_AVAILABLE, TaskMode, TriggerType, LineGrouping)
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt

from ni_specific_heat.ni6003 import Ni6003
from ni_specific_heat.components.preresistor import Preresistor, Resistor
from ni_specific_heat.components.preamplifier import Preamplifier



def calibrate_preresistor(daq, channel, preresistor, nominal_resistance, test_resistance):

	fig, ax = plt.subplots()

	preresistor.set(nominal_resistance)

	excitations = np.arange(-10, 10, 0.2)
	currents = excitations / preresistor.nominal_resistance * 0.5
	voltages = []

	for excitation in excitations:

		daq.analog_write(channel, 0)

		daq.analog_write(channel, -excitation)
		neg = daq.analog_read(channel, 100, 1000)

		daq.analog_write(channel, excitation)
		pos = daq.analog_read(channel, 100, 1000)

		daq.analog_write(channel, 0)

		I = excitation/preresistor.nominal_resistance * 0.5
		V = (np.mean(pos) - np.mean(neg))/2

		voltages.append(V)

	ax.plot(currents, voltages, 'k.')







if __name__ == "__main__":

	daq = Ni6003()

	daq.initialize_digital_output_group('pgia1', 0, 3)

	daq.digital_write('pgia1', [False, False, False, False])
	daq.digital_write('pgia1', [True, False, False, False])
	daq.digital_write('pgia1', [False, False, False, False])

	daq.initialize_digital_output_group('pgia2', 0, 3)

	daq.digital_write('pgia2', [False, False, False, False])
	daq.digital_write('pgia2', [False, True, False, False])
	daq.digital_write('pgia2', [False, False, False, False])


	excitation = 10

	preresistor_1 = Preresistor(daq, 'preresistor_1', {'K0': 4, 'K1': 5})
	preresistor_2 = Preresistor(daq, 'preresistor_2', {'K0': 6, 'K1': 7})

	preresistor_1.add_resistor(1_000, 1_000, config=[True, False])
	preresistor_1.add_resistor(10_000, 10_000, config=[False, False])
	preresistor_1.add_resistor(100_000, 100_000, config=[False, True])

	preresistor_2.add_resistor(1_000, 1_000, config=[True, False])
	preresistor_2.add_resistor(10_000, 10_000, config=[False, False])
	preresistor_2.add_resistor(100_000, 100_000, config=[False, True])


	preresistor_1.set(1000)
	preresistor_2.set(1000)


	calibrate_preresistor(daq, 0, preresistor_1, 10_000, 1_000)
	calibrate_preresistor(daq, 1, preresistor_2, 10_000, 1_000)

	plt.show()