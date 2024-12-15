import numpy as np
import asyncio
from scipy.optimize import curve_fit

from pyacquisition.visa import resource_manager
from pyacquisition.instruments import Clock, Lakeshore_340
from pyacquisition.instruments.lakeshore.lakeshore_340 import InputChannel, OutputChannel



class StageThermometer(object):


	def __init__(self, GPIB, input_channel, output_channel):
		rm = resource_manager('pyvisa')
		self._lake = Lakeshore_340('lakeshore', rm.open_resource(f'GPIB0::{GPIB}::INSTR'))
		self._input_channel = input_channel
		self._output_channel = output_channel

		self.temperature = 0
		self.setpoint = 0
		self.heater_range = 0
		self.heater_power = 0
		self.stable = False
		self._temperature_history = []


	def get_temperature(self, callback=None):
		temperature = self._lake.get_temperature(self._input_channel)
		if callback is not None:
			callback(temperature)
		return temperature


	def get_resistance(self, callback=None):
		resistance = float(self._lake._query(f'SRDG? {self._input_channel.value}'))
		if callback is not None:
			callback(resistance)
		return resistance


	def get_setpoint(self, callback=None):
		setpoint = self._lake.get_setpoint(self._output_channel)
		if callback is not None:
			callback(setpoint)
		return setpoint


	def set_setpoint(self, setpoint, callback=None):
		if setpoint != self.setpoint:
			self.stable = False
			self._temperature_history = []
		self._lake.set_setpoint(self._output_channel, setpoint)
		self.setpoint = setpoint
		if callback is not None:
			callback(setpoint)
		return setpoint


	def get_heater_range(self, callback=None):
		rng = int(self._lake._query('RANGE?'))
		if callback is not None:
			callback(rng)
		return rng


	def set_heater_range(self, rng, callback=None):
		self._lake._command(f'RANGE {rng}')
		if callback is not None:
			callback(rng)
		return rng


	def set_heater_off(self, callback=None):
		self._lake._command('RANGE 0')
		if callback is not None:
			callback(0)
		return 0


	def get_heater_power(self, callback=None):
		power = float(self._lake._query('HTR?'))
		if callback is not None:
			callback(power)
		return power


	def close_to_setpoint(self, temperatures, setpoint, tolerance=10e-3):
		if np.abs(np.mean(temperatures) - setpoint) < tolerance:
			return True
		else:
			return False


	def small_enough_std(self, temperatures, tolerance=10e-3):
		if np.std(temperatures) < tolerance:
			return True
		else:
			return False



	async def monitor(self, period, callback):

		while True:
			await asyncio.sleep(period)
			try:
				self.temperature = self.get_temperature()
				self.setpoint = self.get_setpoint()
				self.heater_range = self.get_heater_range()
				self.heater_power = self.get_heater_power()

				self._temperature_history.append(self.temperature)
				if len(self._temperature_history) > 15:
					self._temperature_history = self._temperature_history[-15:]

				mean_close = self.close_to_setpoint(self._temperature_history, self.setpoint, tolerance=5e-3)
				close = self.close_to_setpoint([self.temperature], self.setpoint, tolerance=5e-3)
				small_spread = self.small_enough_std(self._temperature_history, tolerance=5e-3)

				if mean_close and close and small_spread and len(self._temperature_history)>12:
					self.stable = True
				else:
					self.stable = False

				try:
					func = lambda x, a, b: a + b*x
					x = np.linspace(0, len(self._temperature_history)*period, len(self._temperature_history))
					popt, _ = curve_fit(func, x, self._temperature_history)
					rate = popt[1]*60

				except Exception as e:
					rate = -999


				data = {
					'temperature': self.temperature,
					'setpoint': self.setpoint,
					'rate': rate,
					'heater_range': self.heater_range,
					'heater_power': self.heater_power,
					'stable': self.stable,
				}
				callback(data)
			except Exception as e:
				print(e)
