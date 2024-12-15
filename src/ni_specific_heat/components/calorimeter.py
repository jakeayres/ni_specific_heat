import pandas as pd
import numpy as np
from loguru import logger
from .preamplifier import Preamplifier
from .preresistor import Preresistor





class Calorimeter:


	def __init__(
		self,
		daq,
		name,
		output_channel,
		input_channel,
		preamplifier,
		preresistor,
		):
		self._daq = daq
		self._name = name
		self._output_channel = output_channel
		self._input_channel = input_channel
		self._preamplifier = preamplifier
		self._preresistor = preresistor


	@classmethod
	def from_config(
		cls,
		daq,
		name,
		config_dict,
		):
		preamplifier = Preamplifier(
			daq, 
			config_dict['preamplifier']['name'],
			config_dict['preamplifier']['digital_lines'],
			)
		preresistor = Preresistor(
			daq,
			config_dict['preresistor']['name'],
			config_dict['preresistor']['digital_lines'],
			)

		for i, resistor in enumerate(config_dict['preresistor']['resistors']):
			preresistor.add_resistor(
				resistor['nominal_resistance'],
				resistor['real_resistance'],
				resistor['relay_configuration'],
				set_resistor= i == len(config_dict['preresistor']['resistors'])-1
			)
		return cls(
			daq,
			name,
			config_dict['output_channel'],
			config_dict['input_channel'],
			preamplifier, 
			preresistor,
			)


	@property
	def preamplifier(self):
		return self._preamplifier


	@property
	def preresistor(self):
		return self._preresistor
	


	def _calculate_excitation(self, current):
		return current * self._preresistor.get() * 2.0


	def _calculate_best_preresistor(self, current):
		if np.abs(current) <= 45e-6:
			return 100_000
		elif np.abs(current) <= 450e-6:
			return 10_000
		elif np.abs(current) <= 5e-3:
			return 1_000
		else:
			logger.warning(f'{self._name}: Desired current too large for available resistors')
			logger.warning(f'{self._name}: Setting 1_000 Ohms')
			return 1_000


	def get_appropriate_gain(self, current):
		logger.debug(f'{self._name}: Getting appropriate gain')
		self.set_current(0)
		self.preamplifier.set(1)
		dfs = self._write_and_measure_multiple(
			input_channel=0,
			input_samples=1000,
			input_rate=100000,
			output_channel=0,
			currents=[current, -current],
			)
		self.set_current(0)

		peak = max([dfs[0]['voltage'].abs().max(), dfs[1]['voltage'].abs().max()])
		threshold = 9.8
		if peak > 10.25:
			logger.warning('Selecting gain: Input saturated at lowest gain.')
			return 1
		elif peak < 0.0001:
			logger.warning(f'Selecting gain: Small input ({peak*1000}V) at max gain')
			return 1000
		elif peak > threshold/10:
			logger.debug(f'{self._name}: Appropriate gain found: 1')
			return 1
		elif peak > (threshold/100):
			logger.debug(f'{self._name}: Appropriate gain found: 10')
			return 10
		elif peak > (threshold/1000):
			logger.debug(f'{self._name}: Appropriate gain found: 100')
			return 100
		elif peak > (threshold/10000):
			logger.debug(f'{self._name}: Appropriate gain found: 1000')
			return 1000
		else:
			logger.warning(f'{self._name}: Gain level not captured in elifs')
			logger.warning(f'{self._name}: Returning gain level of 1')
			return 1


	def set_current(self, current, change_resistor=True):
		""" Set a output current either using the currently active preresistor
		or after changing to the most appropraite resistor
		"""
		if change_resistor:
			res = self._calculate_best_preresistor(current)
			self._preresistor.set(res)
		excitation = self._calculate_excitation(current)
		self._daq.analog_write(output_channel=self._output_channel, data=excitation)
		logger.debug(f'{self._name}: Excitation set: {excitation}')


	def _write_and_measure(
		self,
		input_channel,
		input_samples,
		input_rate,
		output_channel,
		current,
		):
		excitation = self._calculate_excitation(current)

		x = self._daq.analog_write_and_read(
			input_channel=input_channel,
			input_samples=input_samples,
			input_rate=input_rate,
			output_channel=output_channel,
			output_value=excitation,
		)

		df = pd.DataFrame(data={
			'time': np.linspace(0, input_samples/input_rate, input_samples),
			'voltage': x,
			'excitation': [excitation]*input_samples,
			'current': [current]*input_samples,
			'preresistor': [self.preresistor.get()]*input_samples,
			})

		return df


	def _write_and_measure_multiple(
		self,
		input_channel,
		input_samples,
		input_rate,
		output_channel,
		currents,
		):

		dfs = []

		for current in currents:
			df = self._write_and_measure(
				input_channel=input_channel,
				input_samples=input_samples,
				input_rate=input_rate,
				output_channel=output_channel,
				current=current,
			)
			dfs.append(df)

		return dfs


	def measure_sweep_section(
		self, 
		preresistor, 
		gain, 
		start_current, 
		measure_current, 
		end_current, 
		rate, 
		samples
		):

		self.set_current(0, change_resistor=False)
		self.preresistor.set(preresistor)
		self.preamplifier.set(gain)
		self.set_current(start_current, change_resistor=False)

		df = self._write_and_measure(
			input_channel=0,
			input_samples=samples,
			input_rate=rate,
			output_channel=0,
			current=measure_current,
		)

		df['gain'] = [gain]*len(df['time'])

		self.set_current(end_current, change_resistor=False)

		return df


	def measure_sweep(
		self, 
		low_current, 
		low_gain, 
		low_preresistor,
		high_current,
		high_gain,
		high_preresistor,
		rate,
		samples,
		):

		positive_rising = self.measure_sweep_section(
			preresistor=high_preresistor,
			gain=high_gain,
			start_current=low_current,
			measure_current=high_current,
			end_current=high_current,
			rate=rate,
			samples=samples,
			)

		positive_falling = self.measure_sweep_section(
			preresistor=low_preresistor,
			gain=low_gain,
			start_current=high_current,
			measure_current=low_current,
			end_current=-low_current,
			rate=rate,
			samples=samples,
			)

		negative_rising = self.measure_sweep_section(
			preresistor=high_preresistor,
			gain=high_gain,
			start_current=-low_current,
			measure_current=-high_current,
			end_current=-high_current,
			rate=rate,
			samples=samples,
			)

		negative_falling = self.measure_sweep_section(
			preresistor=low_preresistor,
			gain=low_gain,
			start_current=-high_current,
			measure_current=-low_current,
			end_current=low_current,
			rate=rate,
			samples=samples,
			)

		return [positive_rising, positive_falling, negative_rising, negative_falling]
