import nidaqmx
from loguru import logger
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
import streamlit as st
from scipy.optimize import curve_fit

from ni_specific_heat.ni6003 import Ni6003
from ni_specific_heat.components.preresistor import Preresistor, Resistor
from ni_specific_heat.components.preamplifier import Preamplifier


@st.cache_resource()
def init_daq():
	return Ni6003()


def linear_fit(x, y, p0=[0, 0]):
	f = lambda x, a, b: a + x*b
	popt, _ = curve_fit(f, x, y)
	return f, popt






def calibrate_preresistor(daq, channel, preresistor, preamplifier, nominal_resistance, gain, test_resistance, excitation):

	fig, ax = plt.subplots(1, 2, figsize=(8, 4))

	preresistor.set(nominal_resistance)
	preamplifier.set(gain)

	max_excitation = excitation

	excitations = np.linspace(-max_excitation, max_excitation, 50, endpoint=True)
	nominal_currents = excitations / preresistor.nominal_resistance * 0.5
	real_currents = excitations / preresistor.real_resistance * 0.5
	voltages = []

	for excitation in excitations:

		daq.analog_write(channel, 0)
		daq.analog_write(channel, -excitation)
		neg = daq.analog_read(channel, 100, 100000)
		daq.analog_write(channel, excitation)
		pos = daq.analog_read(channel, 100, 100000)
		daq.analog_write(channel, 0)

		V = (np.mean(pos) - np.mean(neg))/2

		voltages.append(V/gain)

	ax[0].plot(nominal_currents, voltages, 'k.')
	ax[0].plot(real_currents, voltages, '.', color='tab:blue')
	ax[1].plot(nominal_currents, np.array(voltages)*gain, 'k.')
	ax[1].plot(real_currents, np.array(voltages)*gain, '.', color='tab:blue')

	f, popt_nominal = linear_fit(nominal_currents, voltages, p0=[0, nominal_resistance])
	ax[0].plot(nominal_currents, f(nominal_currents, *popt_nominal), 'r-')
	st.write('Uncalibrated measurement:', popt_nominal[1])

	f, popt_real = linear_fit(real_currents, voltages, p0=[0, nominal_resistance])
	ax[0].plot(real_currents, f(real_currents, *popt_real), 'r-')
	st.write('Calibrated measurement', popt_real[1])


	st.write('New calibrated preresistance is:', test_resistance/popt_nominal[1] * nominal_resistance)
	st.write('Current calibrated preresistance is:', preresistor.real_resistance)

	st.pyplot(fig)




if __name__ == "__main__":

	st.title('DAQ Specific Heat')

	daq = init_daq()


	preamplifier_1 = Preamplifier(daq, 'preamplifier_1', digital_lines={'A0': 2, 'A1': 3, 'WR': 0})
	preamplifier_2 = Preamplifier(daq, 'preamplifier_2', digital_lines={'A0': 2, 'A1': 3, 'WR': 1})


	preamplifier_1.set(1)
	preamplifier_2.set(1)

	preresistor_1 = Preresistor(daq, 'preresistor_1', {'K0': 4, 'K1': 5})
	preresistor_2 = Preresistor(daq, 'preresistor_2', {'K0': 6, 'K1': 7})

	preresistor_1.add_resistor(100_000, 101_801.0, config=[True, False])
	preresistor_1.add_resistor(10_000, 10073.548719501732, config=[False, False])
	preresistor_1.add_resistor(1_000, 996.5791993785064, config=[False, True])

	preresistor_2.add_resistor(100_000, 99_993.2, config=[True, False])
	preresistor_2.add_resistor(10_000, 9998.432931156129, config=[False, False])
	preresistor_2.add_resistor(1_000, 996.6437692184631, config=[False, True])

	calibrate_preresistor(daq, 0, preresistor_1, preamplifier_1, 1_000, 1, 1_000, 0.1)
	calibrate_preresistor(daq, 1, preresistor_2, preamplifier_2, 1_000, 1, 1_000, 0.1)