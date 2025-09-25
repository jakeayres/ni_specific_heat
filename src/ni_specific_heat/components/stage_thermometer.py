import numpy as np
import asyncio
import time
from scipy.optimize import curve_fit
from loguru import logger

from pyacquisition.visa import resource_manager
from pyacquisition.instruments import Clock, Lakeshore_350
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel, OutputChannel, State



class StageThermometer(object):


	def __init__(self, GPIB, input_channel, output_channel):
		rm = resource_manager('pyvisa')
		self._lake = Lakeshore_350('lakeshore', rm.open_resource(f'GPIB0::{GPIB}::INSTR'))
		self._input_channel = input_channel
		self._output_channel = output_channel

		self.temperature = 0
		self.setpoint = 0
		self.ramp_rate = 0
		self.heater_range = 0
		self.heater_power = 0
		self.stable = False
		self._stability_history = []
		self._t0 = time.time()
	

	def _tolerance(self, setpoint):
		return 1e-3 * (3 + 0.02*setpoint + 0.0005*setpoint*setpoint)


	def get_temperature(self, callback=None):
		temperature = self._lake.get_temperature(self._input_channel)
		if callback is not None:
			callback(temperature)
		return temperature


	def get_resistance(self, callback=None):
		resistance = float(self._lake.query(f'SRDG? {self._input_channel.value}'))
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
			self._stability_history = []
		self._lake.set_setpoint(self._output_channel, setpoint)
		self.setpoint = setpoint
		if callback is not None:
			callback(setpoint)
		return setpoint


	def get_ramp_rate(self, callback=None):
		ramp_rate = self._lake.get_ramp(self._output_channel)
		if callback is not None:
			callback(ramp_rate)
		return ramp_rate


	def set_ramp_rate(self, ramp_rate, callback=None):
		self._lake.set_ramp(self._output_channel, State.ON, ramp_rate)
		self.ramp_rate = ramp_rate
		if callback is not None:
			callback(ramp_rate)
		return ramp_rate


	def get_heater_range(self, callback=None):
		rng = int(self._lake._query('RANGE? 1'))
		if callback is not None:
			callback(rng)
		return rng


	def set_heater_range(self, rng, callback=None):
		self._lake._command(f'RANGE 1,{rng}')
		if callback is not None:
			callback(rng)
		return rng


	def set_heater_off(self, callback=None):
		self._lake._command('RANGE 0')
		if callback is not None:
			callback(0)
		return 0


	def get_heater_power(self, callback=None):
		power = float(self._lake.query('HTR?'))
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


	async def stabilize_temperature(self, setpoint, ramp_rate=1, period=2):
		""" Wait for temperature stability at setpoint """
		logger.info(f'Stabilizing {setpoint:.2f} K. (Tol {self._tolerance(setpoint)})')
		self.set_ramp_rate(ramp_rate)
		self.set_setpoint(setpoint)
		while self.stable is False:
			await asyncio.sleep(period)
		logger.info(f'Temperature stable at {setpoint:.2f} K')


	async def ramp_to_temperature(self, setpoint, ramp_rate, period=2):
		""" Ramp to a desired setpoint """
		logger.info(f'Setpoint ramping to {setpoint}K @ {ramp_rate}K/min')
		self.set_ramp_rate(ramp_rate)
		self.set_setpoint(setpoint)
		while self.get_setpoint() != setpoint:
			await asyncio.sleep(period)
		logger.info(f'Setpoint reached {setpoint}K')



	async def monitor(self, period, callback):
		""" Poll the lakeshore """

		while True:
			await asyncio.sleep(period)
			try:
				self.temperature = self.get_temperature()
				self.setpoint = self.get_setpoint()
				self.ramp_rate = self.get_ramp_rate()
				self.heater_range = self.get_heater_range()
				self.heater_power = self.get_heater_power()

				self._stability_history.append(self.temperature)
				if len(self._stability_history) > 15:
					self._stability_history = self._stability_history[-15:]

				tolerance = self._tolerance(self.setpoint)

				mean_close = self.close_to_setpoint(self._stability_history, self.setpoint, tolerance=tolerance)
				close = self.close_to_setpoint([self.temperature], self.setpoint, tolerance=tolerance)
				small_spread = self.small_enough_std(self._stability_history, tolerance=tolerance)

				if mean_close and close and small_spread and len(self._stability_history)>12:
					self.stable = True
				else:
					self.stable = False

				try:
					func = lambda x, a, b: a + b*x
					x = np.linspace(0, len(self._stability_history)*period, len(self._stability_history))
					popt, _ = curve_fit(func, x, self._stability_history)
					rate = popt[1]*60

				except Exception as e:
					rate = -999


				data = {
					'time': time.time() - self._t0,
					'temperature': self.temperature,
					'setpoint': self.setpoint,
					'rate': rate,
					'ramp_rate': self.ramp_rate,
					'heater_range': self.heater_range,
					'heater_power': self.heater_power,
					'stable': self.stable,
				}
				callback(data)
			except Exception as e:
				print(e)
