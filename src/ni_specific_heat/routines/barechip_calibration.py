import asyncio
import numpy as np
import pandas as pd
from loguru import logger
from functools import partial
import dearpygui.dearpygui as gui

from ..ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ..ui.inputs import DecimalInput, IntegerInput, StringInput
from ..ui.plot import Plot


async def set_setpoint_to_current_temperature(experiment):
	temperature = experiment.stage_thermometer.get_temperature()
	ramp_rate = experiment.stage_thermometer.get_ramp_rate()

	experiment.stage_thermometer.set_ramp_rate(0)
	await asyncio.sleep(0.010)
	experiment.stage_thermometer.set_setpoint(temperature)
	await asyncio.sleep(0.010)
	experiment.stage_thermometer.set_ramp_rate(ramp_rate)

	return 0



async def measure_datapoint(
	experiment,
	file_stem,
	minimum_temperature,
	maximum_temperature,
	temperature_steps,
	minimum_current,
	maximum_current,
	current_steps,
	repeats,
	plot,
	):

	df_1 = pd.DataFrame(data={'setpoint': [], 'temperature': [], 'resistance': [], 'current': []})
	df_2 = pd.DataFrame(data={'setpoint': [], 'temperature': [], 'resistance': [], 'current': []})
	temperatures = np.geomspace(minimum_temperature, maximum_temperature, temperature_steps)
	currents = np.geomspace(minimum_current, maximum_current, current_steps)

	plot.delete_all_series()
	plot.add_series(f'A', [], [])
	plot.add_series(f'B', [], [])

	gain_1 = 1
	gain_2 = 1

	await set_setpoint_to_current_temperature(experiment)

	for setpoint in temperatures:

		if setpoint < 3.0:
			experiment.stage_thermometer.set_heater_range(2)
		elif setpoint < 10.0:
			experiment.stage_thermometer.set_heater_range(3)
		elif setpoint < 20.0:
			experiment.stage_thermometer.set_heater_range(4)

		await experiment.stage_thermometer.stabilize_temperature(setpoint=setpoint, ramp_rate=1)
		await asyncio.sleep(60)

		for current in currents:
			logger.info(f'Calibrating at {setpoint}K and {current*1e6}uA')

			# Set best preresistor
			preresistor_1 = experiment.calorimeters[0].calculate_best_preresistor(current)
			preresistor_2 = experiment.calorimeters[1].calculate_best_preresistor(current)	

			for i in range(repeats):

				data_1 = await experiment.calorimeters[0].measure_resistance(
					current=current,
					gain=gain_1,
					preresistor=preresistor_1,
					)
				data_2 = await experiment.calorimeters[1].measure_resistance(
					current=current,
					gain=gain_2,
					preresistor=preresistor_2,
					)

				# Autorange the gain
				if data_1['voltage'] < 0.5:
					gain_1 = min(gain_1 * 10, 1000) 
				elif data_1['voltage'] > 8.0:
					gain_1 = max(gain_1 / 10, 1)

				if data_2['voltage'] < 0.5:
					gain_2 = min(gain_2 * 10, 1000) 
				elif data_2['voltage'] > 8.0:
					gain_2 = max(gain_2 / 10, 1)

				plot.append_series(f'A', [current], [data_1['resistance']])
				plot.append_series(f'B', [current], [data_2['resistance']])

				temperature = experiment.stage_thermometer.get_temperature()

				df_1.loc[len(df_1)] = [
					setpoint, 
					temperature,
					data_1['resistance'],
					current,
					]

				df_2.loc[len(df_2)] = [
					setpoint, 
					temperature,
					data_2['resistance'],
					current,
					]


			df_1.to_csv(f'C://Data/{file_stem}_A.dat', index=False)
			df_2.to_csv(f'C://Data/{file_stem}_B.dat', index=False)



	


def make_barechip_calibrations(
	experiment,
	):

	window = gui.add_window(label='Make Barechip Calibration', pos=(550, 150), width=550)
	main_plot = Plot.add_to_parent(window, height=400, width=-1)

	columns = gui.add_group(parent=window, horizontal=True, horizontal_spacing=75, width=125)
	left = gui.add_group(parent=columns, width=200)
	right = gui.add_group(parent=columns, width=200)

	minimum_temperature = DecimalInput.add_to_parent(left, 'T Minimum', value=1.50, unit='K')
	maximum_temperature = DecimalInput.add_to_parent(left, 'T Maximum', value=15.00, unit='K')
	temperature_steps = IntegerInput.add_to_parent(left, 'T Steps', value=10)

	minimum_current = DecimalInput.add_to_parent(right, 'I Minimum', value=10.00, unit='uA')
	maximum_current = DecimalInput.add_to_parent(right, 'I Maximum', value=1000.00, unit='uA')
	current_steps = IntegerInput.add_to_parent(right, 'I Steps', value=10)
	repeats = IntegerInput.add_to_parent(right, 'Repeats', value=10)

	file_stem = StringInput.add_to_parent(window, 'File stem', value='calibration')

	
	gui.add_button(
		parent=window,
		label='Add calibration point', 
		callback=lambda: experiment.tasks.append(
			partial(
				measure_datapoint,
				experiment=experiment,
				file_stem=file_stem.value,
				minimum_temperature=minimum_temperature.value,
				maximum_temperature=maximum_temperature.value,
				temperature_steps=temperature_steps.value,
				minimum_current=minimum_current.value * 1e-6,
				maximum_current=maximum_current.value * 1e-6,
				current_steps=current_steps.value,
				repeats=repeats.value,
				plot=main_plot,
			)),
		)
	
