import nidaqmx
import json
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


CONFIG_PATH = 'calorimeter_config.json'


@st.cache_resource()
def init_daq():
	daq = Ni6003()
	return daq


def linear_fit(x, y, p0=[0, 0]):
	f = lambda x, a, b: a + x*b
	popt, _ = curve_fit(f, x, y)
	return f, popt


def read_config():
	with open(CONFIG_PATH, 'r') as file:
		data = json.load(file)
	return data


def save_config(config):
	with open(CONFIG_PATH, 'w') as file:
		json.dump(config, file, indent=4)



if __name__ == "__main__":

	st.title('Calibrate Preresistors')
	daq = init_daq()
	config = read_config()
	st.write(config)

	preamplifier_1 = Preamplifier(daq, 'preamplifier_1', digital_lines={'A0': 2, 'A1': 3, 'WR': 0})
	preamplifier_2 = Preamplifier(daq, 'preamplifier_2', digital_lines={'A0': 2, 'A1': 3, 'WR': 1})

	preamplifier_1.set(1)
	preamplifier_2.set(1)

	preresistor_1 = Preresistor(daq, 'preresistor_1', {'K0': 4, 'K1': 5})
	preresistor_2 = Preresistor(daq, 'preresistor_2', {'K0': 6, 'K1': 7})





	if st.button('Save'):
		save_config(config)

