from loguru import logger
import numpy as np
import pandas as pd
import time
import json
import matplotlib.pyplot as plt
import asyncio
import dearpygui.dearpygui as gui
from functools import partial

from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel, OutputChannel

from src.ni_specific_heat.ni6003 import Ni6003
from src.ni_specific_heat.components.calorimeter import Calorimeter
from src.ni_specific_heat.components.stage_thermometer import StageThermometer
from src.ni_specific_heat.components.barechip_calibration import BarechipCalibration

from src.ni_specific_heat.ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from src.ni_specific_heat.ui.inputs import DecimalInput, IntegerInput, StringInput
from src.ni_specific_heat.ui.plot import Plot


from src.ni_specific_heat.routines.barechip_calibration import make_barechip_calibrations
from src.ni_specific_heat.routines.relaxation import setup_relaxations, setup_single_relaxation


class CpExperiment:


	def __init__(self):

		self.calorimeters = self._load_calorimeters('calorimeter_config.json')
		self.calibrations = [BarechipCalibration(), BarechipCalibration()]
		self.stage_thermometer = StageThermometer(GPIB=2, input_channel=InputChannel.INPUT_A, output_channel=OutputChannel.OUTPUT_1)
		self.tasks = []


	def _load_calorimeters(self, fname: str):
		daq = Ni6003()
		f = fname
		with open(f, 'r') as file:
			data = json.load(file)
		cal_1 = Calorimeter.from_config(daq, 'Cal1', data['calorimeter_1'])
		cal_2 = Calorimeter.from_config(daq, 'Cal2', data['calorimeter_2'])
		return [cal_1, cal_2]


	def _initialize_dearpygui(self):
		gui.create_context()
		gui.create_viewport(title='Custom Title', width=1600, height=800)
		gui.setup_dearpygui()


	async def setup_gui(self):

		""" The stage window
		"""
		stage_window = gui.add_window(label='Stage Status', pos=(0, 0), width=300)
		self.live_temperature_plot = Plot.add_to_parent(stage_window, height=200, width=-1)
		gui.add_button(
			parent=stage_window, 
			label='Clear plot', 
			callback=self.live_temperature_plot.clear_all_series,
			)
		self.temperature_indicator = DecimalIndicator.add_to_parent(stage_window, 'Temperature', 0, unit='K')
		self.temperature_rate_indicator = DecimalIndicator.add_to_parent(stage_window, 'Rate', 0, unit='K/min')
		self.setpoint_indicator = DecimalIndicator.add_to_parent(stage_window, 'Setpoint', 0, unit='K')
		self.ramp_rate_indicator = DecimalIndicator.add_to_parent(stage_window, 'Ramp rate', 0, unit='K/min')
		self.heater_range_indicator = IntegerIndicator.add_to_parent(stage_window, 'Heater range', 0)
		self.heater_power_indicator = DecimalIndicator.add_to_parent(stage_window, 'Heater power', 0, unit='%')
		self.stable_indicator = BooleanIndicator.add_to_parent(stage_window, 'Stable', 0)
		self.live_temperature_plot.add_series('temperature', [], [])
		self.live_temperature_plot.add_series('setpoint', [], [])
		setpoint_input = DecimalInput.add_to_parent(stage_window, 'Setpoint', value=290.00, unit='K')
		ramp_rate_input = DecimalInput.add_to_parent(stage_window, 'Ramp rate', value=5.00, unit='K/min')
		gui.add_button(
			parent=stage_window, 
			label='Ramp to', 
			callback=lambda: partial(
				self.queue_ramp_temperature,
				setpoint=setpoint_input.value,
				ramp_rate=ramp_rate_input.value,
				)(),
			)
		gui.add_button(
			parent=stage_window, 
			label='Stabilize', 
			callback=lambda: partial(
				self.queue_stabilize_temperature,
				setpoint=setpoint_input.value,
				)(),
			)

		""" Calorimeter window 1
		"""
		calorimeter_window_1 = gui.add_window(label='Calorimeter A', pos=(950, 0), width=300)
		self.live_voltage_plot_1 = Plot.add_to_parent(calorimeter_window_1, height=200, width=-1, yaxis_kwargs={})
		self.preresistor_indicator_1 = IntegerIndicator.add_to_parent(calorimeter_window_1, 'Preresistor', 1000, unit='Ohms')
		self.excitation_indicator_1 = DecimalIndicator.add_to_parent(calorimeter_window_1, 'Excitation', 0, unit='V')
		self.current_indicator_1 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_1, 'Current', 0, unit='A')
		self.voltage_gain_indicator_1 = IntegerIndicator.add_to_parent(calorimeter_window_1, 'Voltage gain', 1, unit='x')
		self.mean_voltage_indicator_1 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_1, 'Voltage', 0, unit='V')
		self.resistance_indicator_1 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_1, 'Resistance', 0, unit='Ohms')

		self.calorimeters[0].preresistor.add_callback(self.preresistor_indicator_1.set_value)
		self.calorimeters[0].preamplifier.add_callback(self.voltage_gain_indicator_1.set_value)
		self.calorimeters[0]._current_callback = self.current_indicator_1.set_value
		self.calorimeters[0]._excitation_callback = self.excitation_indicator_1.set_value
		self.calorimeters[0]._voltage_callback = self.mean_voltage_indicator_1.set_value
		self.calorimeters[0]._resistance_callback = self.resistance_indicator_1.set_value

		gui.add_separator(parent=calorimeter_window_1)
		with gui.group(horizontal=True, parent=calorimeter_window_1):
			gui.add_button(
				label='1x', 
				callback=lambda: partial(
					self.calorimeters[0].preamplifier.set, 
					gain=1, 
					)(),
				)
			gui.add_button(
				label='10x', 
				callback=lambda: partial(
					self.calorimeters[0].preamplifier.set, 
					gain=10, 
					)(),
				)
			gui.add_button(
				label='100x', 
				callback=lambda: partial(
					self.calorimeters[0].preamplifier.set, 
					gain=100, 
					)(),
				)
			gui.add_button(
				label='1000x', 
				callback=lambda: partial(
					self.calorimeters[0].preamplifier.set, 
					gain=1000, 
					)(),
				)

		with gui.group(horizontal=True, parent=calorimeter_window_1):
			gui.add_button(
				label='1kOhms', 
				callback=lambda: partial(
					self.calorimeters[0].preresistor.set, 
					resistance=1000,
					)(),
				)
			gui.add_button(
				label='10kOhms', 
				callback=lambda: partial(
					self.calorimeters[0].preresistor.set, 
					resistance=10000, 
					)(),
				)
			gui.add_button(
				label='100kOhms', 
				callback=lambda: partial(
					self.calorimeters[0].preresistor.set, 
					resistance=100000, 
					)(),
				)

		gui.add_separator(parent=calorimeter_window_1)
		current_input_1 = DecimalInput.add_to_parent(calorimeter_window_1, 'Current', value=0.00, unit='mA')
		measure_samples_input_1 = IntegerInput.add_to_parent(calorimeter_window_1, 'Samples', value=50000)
		measure_time_input_1 = DecimalInput.add_to_parent(calorimeter_window_1, 'Time', value=1.00, unit='s')
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Queue measure', 
			callback=lambda: partial(
				self.queue_measure_resistance,
				calorimeter=0,
				current=current_input_1.value*1e-3,
				time=measure_time_input_1.value,
				samples=measure_samples_input_1.value,
				)(),
			)

		gui.add_separator(parent=calorimeter_window_1)
		gui.add_text('Barechip Calibration', parent=calorimeter_window_1)
		self.calibration_plot_1 = Plot.add_to_parent(calorimeter_window_1, height=200, width=-1, yaxis_kwargs={})
		gui.add_button(
			parent=calorimeter_window_1,
			label='Assign Calibration', 
			callback=self.calorimeters[0].calibration.open_calibration_data_dialog,
			user_data={'plot': self.calibration_plot_1}
			)

		self.calorimeters[0].preresistor.get(callback=self.preresistor_indicator_1.set_value)
		self.calorimeters[0].preamplifier.get(callback=self.voltage_gain_indicator_1.set_value)

		""" Calorimeter window 2
		"""
		calorimeter_window_2 = gui.add_window(label='Calorimeter B', pos=(1250, 0), width=300)
		self.live_voltage_plot_2 = Plot.add_to_parent(calorimeter_window_2, height=200, width=-1, yaxis_kwargs={})
		self.preresistor_indicator_2 = IntegerIndicator.add_to_parent(calorimeter_window_2, 'Preresistor', 1000, unit='Ohms')
		self.excitation_indicator_2 = DecimalIndicator.add_to_parent(calorimeter_window_2, 'Excitation', 0, unit='V')
		self.current_indicator_2 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_2, 'Current', 0, unit='A')
		self.voltage_gain_indicator_2 = IntegerIndicator.add_to_parent(calorimeter_window_2, 'Voltage gain', 1, unit='x')
		self.mean_voltage_indicator_2 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_2, 'Voltage', 0, unit='V')
		self.resistance_indicator_2 = ScientificDecimalIndicator.add_to_parent(calorimeter_window_2, 'Resistance', 0, unit='Ohms')

		self.calorimeters[1].preresistor.add_callback(self.preresistor_indicator_2.set_value)
		self.calorimeters[1].preamplifier.add_callback(self.voltage_gain_indicator_2.set_value)
		self.calorimeters[1].preresistor.add_callback(self.preresistor_indicator_2.set_value)
		self.calorimeters[1].preamplifier.add_callback(self.voltage_gain_indicator_2.set_value)
		self.calorimeters[1]._current_callback = self.current_indicator_2.set_value
		self.calorimeters[1]._excitation_callback = self.excitation_indicator_2.set_value
		self.calorimeters[1]._voltage_callback = self.mean_voltage_indicator_2.set_value
		self.calorimeters[1]._resistance_callback = self.resistance_indicator_2.set_value

		gui.add_separator(parent=calorimeter_window_2)
		with gui.group(horizontal=True, parent=calorimeter_window_2):
			gui.add_button(
				label='1x', 
				callback=lambda: partial(
					self.calorimeters[1].preamplifier.set, 
					gain=1, 
					)(),
				)
			gui.add_button(
				label='10x', 
				callback=lambda: partial(
					self.calorimeters[1].preamplifier.set, 
					gain=10, 
					)(),
				)
			gui.add_button(
				label='100x', 
				callback=lambda: partial(
					self.calorimeters[1].preamplifier.set, 
					gain=100, 
					)(),
				)
			gui.add_button(
				label='1000x', 
				callback=lambda: partial(
					self.calorimeters[1].preamplifier.set, 
					gain=1000, 
					)(),
				)

		with gui.group(horizontal=True, parent=calorimeter_window_2):
			gui.add_button(
				label='1kOhms', 
				callback=lambda: partial(
					self.calorimeters[1].preresistor.set, 
					resistance=1000, 
					)(),
				)
			gui.add_button(
				label='10kOhms', 
				callback=lambda: partial(
					self.calorimeters[1].preresistor.set, 
					resistance=10000, 
					)(),
				)
			gui.add_button(
				label='100kOhms', 
				callback=lambda: partial(
					self.calorimeters[1].preresistor.set, 
					resistance=100000, 
					)(),
				)

		gui.add_separator(parent=calorimeter_window_2)
		current_input_2 = DecimalInput.add_to_parent(calorimeter_window_2, 'Current', value=0.00, unit='mA')
		measure_samples_input_2 = IntegerInput.add_to_parent(calorimeter_window_2, 'Samples', value=50000)
		measure_time_input_2 = DecimalInput.add_to_parent(calorimeter_window_2, 'Time', value=1.00, unit='s')
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Queue measure', 
			callback=lambda: partial(
				self.queue_measure_resistance,
				calorimeter=1,
				current=current_input_2.value*1e-3,
				time=measure_time_input_2.value,
				samples=measure_samples_input_2.value,
				)(),
			)

		gui.add_separator(parent=calorimeter_window_2)
		gui.add_text('Barechip Calibration', parent=calorimeter_window_2)
		self.calibration_plot_2 = Plot.add_to_parent(calorimeter_window_2, height=200, width=-1, yaxis_kwargs={})
		gui.add_button(
			parent=calorimeter_window_2,
			label='Assign Calibration', 
			callback=self.calorimeters[1].calibration.open_calibration_data_dialog,
			user_data={'plot': self.calibration_plot_2}
			)

		self.calorimeters[1].preresistor.get(callback=self.preresistor_indicator_2.set_value)
		self.calorimeters[1].preamplifier.get(callback=self.voltage_gain_indicator_2.set_value)

		""" MAIN COMMANDS
		"""

		with gui.window(label='Commands', pos=(400, 0), width=300):

			gui.add_button(
				label='Make barechip calibrations',
				callback=self.queue_make_barechip_calibration,
			)

			gui.add_button(
				label='Single Relaxation',
				callback=self.queue_single_relaxation,
			)

			gui.add_button(
				label='Setup long relaxations',
				callback=self.queue_setup_relaxations,
			)



	def update_stage_indicators(self, data):
		self.temperature_indicator.set_value(data['temperature'])
		self.temperature_rate_indicator.set_value(data['rate'])
		self.setpoint_indicator.set_value(data['setpoint'])
		self.ramp_rate_indicator.set_value(data['ramp_rate'])
		self.heater_range_indicator.set_value(data['heater_range'])
		self.heater_power_indicator.set_value(data['heater_power'])
		self.stable_indicator.set_value(data['stable'])

		self.live_temperature_plot.append_series('temperature', [data['time']], [data['temperature']])
		self.live_temperature_plot.append_series('setpoint', [data['time']], [data['setpoint']])


	def update_calorimeter_indicators(self, calorimeter, data):
		self.excitation_indicator_1.set_value(data['excitation'])
		self.current_indicator_1.set_value()



	def queue_measure_resistance(
		self,
		calorimeter: int,
		current: float,
		time: float,
		samples: int,
		):

		plot = self.live_voltage_plot_1 if calorimeter == 0 else self.live_voltage_plot_2
		rate=int(samples/time)

		self.tasks.append(partial(
			self.calorimeters[calorimeter].measure_resistance,
			current=current,
			plot=plot,
			rate=rate,
			samples=samples,
		))


	def queue_stabilize_temperature(
		self,
		setpoint: float,
		):
		self.tasks.append(partial(
			self.stage_thermometer.stabilize_temperature,
			setpoint=setpoint,
		))


	def queue_ramp_temperature(
		self,
		setpoint: float,
		ramp_rate: float,
		):
		self.tasks.append(partial(
			self.stage_thermometer.ramp_to_temperature,
			setpoint=setpoint,
			ramp_rate=ramp_rate,
		))


	def queue_make_barechip_calibration(self):
		make_barechip_calibrations(experiment=self)


	def queue_single_relaxation(self):
		setup_single_relaxation(experiment=self)
			

	def queue_setup_relaxations(self):
		setup_relaxations(experiment=self)



	""" Core asyncio methods
	"""

	async def _render(self):
		""" The render loop
		"""
		while gui.is_dearpygui_running():
			gui.render_dearpygui_frame()
			await asyncio.sleep(0.010)
		else:
			gui.destroy_context()


	async def _run(self):
		""" Experiment run loop executing tasks in task queue
		"""
		while True:
			await asyncio.sleep(1)
			try:
				if len(self.tasks) > 0:
					task = self.tasks.pop(0)
					await task()
			except Exception as e:
				logger.error('Task raised an exception')
				logger.opt(exception=e).warning("Logging exception traceback")


	async def run(self):
		""" The main asyncio entry point
		"""
		self._initialize_dearpygui()
		await self.setup_gui()
		gui.show_viewport()

		done, pending = await asyncio.wait(
			[
				asyncio.create_task(self._render()),
				asyncio.create_task(self._run()),
				asyncio.create_task(self.stage_thermometer.monitor(2, callback=self.update_stage_indicators)),
			],
			return_when=asyncio.FIRST_EXCEPTION,
		)

		gui.destroy_context()



if __name__ == "__main__":

	logger.debug('Code running')

	exp = CpExperiment()
	asyncio.run(exp.run())