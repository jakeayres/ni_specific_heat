from loguru import logger
from ni_specific_heat.ni6003 import Ni6003
from ni_specific_heat.components.calorimeter import Calorimeter
import json, time
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt





if __name__ == "__main__":

	daq = Ni6003()
	logger.debug('------ BREAK -------')

	f = 'calorimeter_config.json'
	with open(f, 'r') as file:
		data = json.load(file)

	st.title('Calorimeter')


	cal_1 = Calorimeter.from_config(daq, 'Cal1', data['calorimeter_1'])
	cal_2 = Calorimeter.from_config(daq, 'Cal2', data['calorimeter_2'])



	fig, ax = plt.subplots(2, 1, figsize=(8, 8))
	plot = st.pyplot(fig)
	time.sleep(1)



	with plot:

		dfs = cal_1.measure_sweep(
			low_current=1e-4, 
			low_gain=10, 
			low_preresistor=1_000,
			high_current=5e-4,
			high_gain=10,
			high_preresistor=1_000,
			rate=50_000,
			samples=1_000,
		)

		for i, df in enumerate(dfs):
			ax[0].plot(df['time'], df['voltage'], label=f'{i}')
		ax[0].legend(frameon=False)

		st.pyplot(fig)

		dfs = cal_2.measure_sweep(
			low_current=0.5e-4, 
			low_gain=10, 
			low_preresistor=1_000,
			high_current=2.5e-4,
			high_gain=10,
			high_preresistor=1_000,
			rate=50_000,
			samples=1_000,
		)

		for i, df in enumerate(dfs):
			ax[1].plot(df['time'], df['voltage'], label=f'{i}')
		ax[1].legend(frameon=False)

		st.pyplot(fig)
