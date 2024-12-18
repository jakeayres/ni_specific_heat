import asyncio
import numpy as np
import pandas as pd
from loguru import logger
from functools import partial
import dearpygui.dearpygui as gui

from ni_specific_heat.ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ni_specific_heat.ui.inputs import DecimalInput, IntegerInput, StringInput
from ni_specific_heat.ui.plot import Plot


def calculate_low_current(temperature):
	return 1e-6 * (10 + 0.1*temperature + 0.0005*temperature*temperature)


def calculate_low_preresistor(current):
	pass


def calculate_expected_signal_voltage(current, temperature, calorimeter):
	expected_resistance = calorimeter.calibration.evaluate_resistance(temperature)
	expected_voltage = expected_resistance * current
	return expected_voltage


def calculate_preamplifier_gain(current, temperature, calorimeter):
	voltage = calculate_expected_signal_voltage(current, temperature, calorimeter)
	threshold = 9.8
	if voltage > 10.25:
		logger.warning('Selecting gain: Input saturated at lowest gain.')
		return 1
	elif voltage < 0.0001:
		logger.warning(f'Selecting gain: Small input ({voltage*1000}V) at max gain')
		return 1000
	elif voltage > threshold/10:
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 1')
		return 1
	elif voltage > (threshold/100):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 10')
		return 10
	elif voltage > (threshold/1000):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 100')
		return 100
	elif voltage > (threshold/10000):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 1000')
		return 1000
	else:
		logger.warning(f'{calorimeter._name}: Gain level not captured in elifs')
		logger.warning(f'{calorimeter._name}: Returning gain level of 1')
		return 1



async def perform_relaxations(
	experiment,
	file_stem,
	minimum_temperature,
	maximum_temperature,
	temperature_steps,
	relaxation_size,
	repeats,
	plot,
	):

	logger.info('Starting relaxations')
	temperatures = np.geomspace(minimum_temperature, maximum_temperature, temperature_steps)

	plot.delete_all_series()

	for temperature in temperatures:

		low_current = calculate_low_current(temperature)
		low_preresistor = experiment.calorimeters[0].calculate_best_preresistor(low_current)
		low_gain = calculate_preamplifier_gain(low_current, temperature, experiment.calorimeters[0])

		high_current = 1e-3
		high_preresistor = experiment.calorimeters[0].calculate_best_preresistor(high_current)
		high_gain = calculate_preamplifier_gain(high_current, temperature, experiment.calorimeters[0])

		logger.info(f'{low_current}, {low_preresistor}, {low_gain}')

		positive_rising, positive_falling, negative_rising, negative_falling = await experiment.calorimeters[0].measure_sweep(
			low_current=low_current, 
			low_gain=1, 
			low_preresistor=1000,
			high_current=high_current,
			high_gain=1,
			high_preresistor=1000,
			rate=20_000,
			samples=90_000,
			plot=plot,
		)



def setup_relaxations(
	experiment,
	):

	window = gui.add_window(label='Long Relaxation', pos=(550, 150), width=550)
	main_plot = Plot.add_to_parent(window, height=400, width=-1)

	columns = gui.add_group(parent=window, horizontal=True, horizontal_spacing=75, width=125)
	left = gui.add_group(parent=columns, width=200)
	right = gui.add_group(parent=columns, width=200)

	minimum_temperature = DecimalInput.add_to_parent(left, 'T Minimum', value=1.50, unit='K')
	maximum_temperature = DecimalInput.add_to_parent(left, 'T Maximum', value=3.00, unit='K')
	temperature_steps = IntegerInput.add_to_parent(left, 'T Steps', value=2)
	relaxation_size = DecimalInput.add_to_parent(left, 'Relaxation size', value=1.40, unit='x')

	repeats = IntegerInput.add_to_parent(right, 'Repeats', value=5)

	file_stem = StringInput.add_to_parent(window, 'File stem', value='relaxation')

	gui.add_button(
		parent=window,
		label='Start relaxation', 
		callback=lambda: experiment.tasks.append(
			partial(
				perform_relaxations,
				experiment=experiment,
				file_stem=file_stem.value,
				minimum_temperature=minimum_temperature.value,
				maximum_temperature=maximum_temperature.value,
				temperature_steps=temperature_steps.value,
				relaxation_size=relaxation_size.value,
				repeats=repeats.value,
				plot=main_plot,
			)),
		)