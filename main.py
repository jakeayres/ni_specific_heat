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

from ni_specific_heat.ni6003 import Ni6003
from ni_specific_heat.components.calorimeter import Calorimeter
from ni_specific_heat.components.stage_thermometer import StageThermometer
from ni_specific_heat.components.barechip_calibration import BarechipCalibration

from ni_specific_heat.ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ni_specific_heat.ui.inputs import DecimalInput, IntegerInput, StringInput
from ni_specific_heat.ui.plot import Plot


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
		gui.create_viewport(title='Custom Title', width=1100, height=600)
		gui.setup_dearpygui()


	async def setup_gui(self):

		""" The stage window
		"""
		stage_window = gui.add_window(label='Stage Status', pos=(0, 0), width=300)
		self.live_temperature_plot = Plot.add_to_parent(stage_window, height=200, width=-1)
		self.temperature_indicator = ScientificDecimalIndicator.add_to_parent(stage_window, 'Temperature', 0, unit='K')
		self.temperature_rate_indicator = ScientificDecimalIndicator.add_to_parent(stage_window, 'Rate', 0, unit='K/min')
		self.setpoint_indicator = ScientificDecimalIndicator.add_to_parent(stage_window, 'Setpoint', 0, unit='K')
		self.heater_range_indicator = IntegerIndicator.add_to_parent(stage_window, 'Heater range', 0)
		self.heater_power_indicator = DecimalIndicator.add_to_parent(stage_window, 'Heater power', 0, unit='%')
		self.stable_indicator = BooleanIndicator.add_to_parent(stage_window, 'Stable', 0)
		self.live_temperature_plot.add_series('temperature')


		""" Calorimeter window 1
		"""
		calorimeter_window_1 = gui.add_window(label='Calorimeter A', pos=(300, 0), width=300)
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

		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Gain 1', 
			callback=lambda: partial(
				self.calorimeters[0].preamplifier.set, 
				gain=1, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Gain 10', 
			callback=lambda: partial(
				self.calorimeters[0].preamplifier.set, 
				gain=10, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Gain 100', 
			callback=lambda: partial(
				self.calorimeters[0].preamplifier.set, 
				gain=100, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Gain 1000', 
			callback=lambda: partial(
				self.calorimeters[0].preamplifier.set, 
				gain=1000, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Preres 1kOhms', 
			callback=lambda: partial(
				self.calorimeters[0].preresistor.set, 
				resistance=1000,
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Preres 10kOhms', 
			callback=lambda: partial(
				self.calorimeters[0].preresistor.set, 
				resistance=10000, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_1, 
			label='Set Preres 100kOhms', 
			callback=lambda: partial(
				self.calorimeters[0].preresistor.set, 
				resistance=100000, 
				)(),
			)

		self.calorimeters[0].preresistor.get(callback=self.preresistor_indicator_1.set_value)
		self.calorimeters[0].preamplifier.get(callback=self.voltage_gain_indicator_1.set_value)

		""" Calorimeter window 2
		"""
		calorimeter_window_2 = gui.add_window(label='Calorimeter B', pos=(600, 0), width=300)
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

		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Gain 1', 
			callback=lambda: partial(
				self.calorimeters[1].preamplifier.set, 
				gain=1, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Gain 10', 
			callback=lambda: partial(
				self.calorimeters[1].preamplifier.set, 
				gain=10, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Gain 100', 
			callback=lambda: partial(
				self.calorimeters[1].preamplifier.set, 
				gain=100, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Gain 1000', 
			callback=lambda: partial(
				self.calorimeters[1].preamplifier.set, 
				gain=1000, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Preres 1kOhms', 
			callback=lambda: partial(
				self.calorimeters[1].preresistor.set, 
				resistance=1000, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Preres 10kOhms', 
			callback=lambda: partial(
				self.calorimeters[1].preresistor.set, 
				resistance=10000, 
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Set Preres 100kOhms', 
			callback=lambda: partial(
				self.calorimeters[1].preresistor.set, 
				resistance=100000, 
				)(),
			)

		self.calorimeters[1].preresistor.get(callback=self.preresistor_indicator_2.set_value)
		self.calorimeters[1].preamplifier.get(callback=self.voltage_gain_indicator_2.set_value)

		gui.add_button(
			parent=calorimeter_window_1, 
			label='Queue measure', 
			callback=lambda: partial(
				self.queue_measure_resistance,
				calorimeter=0,
				)(),
			)
		gui.add_button(
			parent=calorimeter_window_2, 
			label='Queue measure', 
			callback=lambda: partial(
				self.queue_measure_resistance,
				calorimeter=1,
				)(),
			)



	def update_stage_indicators(self, data):
		self.temperature_indicator.set_value(data['temperature'])
		self.temperature_rate_indicator.set_value(data['rate'])
		self.setpoint_indicator.set_value(data['setpoint'])
		self.heater_range_indicator.set_value(data['heater_range'])
		self.heater_power_indicator.set_value(data['heater_power'])
		self.stable_indicator.set_value(data['stable'])

		self.live_temperature_plot.up


	def update_calorimeter_indicators(self, calorimeter, data):
		self.excitation_indicator_1.set_value(data['excitation'])
		self.current_indicator_1.set_value()



	def queue_measure_resistance(
		self,
		calorimeter: int,
		):

		plot = self.live_voltage_plot_1 if calorimeter == 0 else self.live_voltage_plot_2

		self.tasks.append(partial(
			self.calorimeters[calorimeter].measure_resistance,
			current=1e-4,
			plot=plot
		))


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

	exp = CpExperiment()
	asyncio.run(exp.run())