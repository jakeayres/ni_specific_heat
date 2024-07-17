import pandas as pd
import numpy as np
from loguru import logger
from .preamplifier import Preamplifier
from .preresistor import Preresistor




class Calorimeter:


	PRERESISTOR_MAP = {
		1_000: 1000 * 1.0163,
		100_000: 100_000 / 1.0163,
	}


	def __init__(
		self, 
		daq, 
		preamp_digital_lines,
		):

		self._daq = daq
		self._daq.initialize_digital_output_group('preresistor', 3, 3)

		self.preamplifier = Preamplifier(daq, digital_lines=preamp_digital_lines)
		self.nominal_preresistor = None

		self.set_preresistor(100_000)


	def _set_100k_presresistor(self, callback=None):
		self._daq.digital_output_groups['preresistor'].write([True])
		self.nominal_preresistor = 100_000


	def _set_1k_presresistor(self, callback=None):
		self._daq.digital_output_groups['preresistor'].write([False])
		self.nominal_preresistor = 1000


	def set_preresistor(self, preresistor, callback=None):
		if preresistor != self.nominal_preresistor:
			if preresistor == 1000:
				self._set_1k_presresistor(callback=callback)
				logger.debug(f'Preresistor changed: {preresistor}')
			elif preresistor == 100_000:
				self._set_100k_presresistor(callback=callback)
				logger.debug(f'Preresistor changed: {preresistor}')
			else:
				logger.warning(f'Preresistor not changed: {preresistor} not an allowed value.')
		else:
			logger.debug(f'Preresistor not changed: preresistor already at value.')


	@property
	def real_preresistor(self):
		if self.nominal_preresistor == 1_000:
			return self.PRERESISTOR_MAP[1_000]
		elif self.nominal_preresistor == 100_000:
			return self.PRERESISTOR_MAP[100_000]


	def _calculate_excitation(self, current):
		return current*self.real_preresistor


	def write_and_measure(
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
			'preresistor': [self.real_preresistor]*input_samples,
			})

		return df


	def write_and_measure_multiple(
		self,
		input_channel,
		input_samples,
		input_rate,
		output_channel,
		currents,
		):

		dfs = []

		for current in currents:
			df = self.write_and_measure(
				input_channel=input_channel,
				input_samples=input_samples,
				input_rate=input_rate,
				output_channel=output_channel,
				current=current,
			)
			dfs.append(df)

		return dfs


	def get_appropriate_gain(self, current):

		self.set_current(0)
		self.preamplifier.set_gain(1)
		dfs = self.write_and_measure_multiple(
			input_channel=0,
			input_samples=1000,
			input_rate=100000,
			output_channel=0,
			currents=[current, -current],
			)
		self.set_current(0)

		peak = max([dfs[0]['voltage'].abs().max(), dfs[1]['voltage'].abs().max()])
		threshold = 9.8
		if peak > 10.45:
			logger.warning('Selecting gain: Input saturated at lowest gain.')
			return 1
		elif peak < 0.0001:
			logger.warning(f'Selecting gain: Small input ({peak*1000}V) at max gain')
			return 1000
		elif peak > threshold/10:
			return 1
		elif peak > (threshold/100):
			return 10
		elif peak > (threshold/1000):
			return 100
		elif peak > (threshold/10000):
			return 1000


	def set_appropriate_gain(self, current):
		gain = self.get_appropriate_gain(current)
		self.preamplifier.set_gain(gain)


	def get_appropriate_preresistor(self, current):
		if current <= 90e-6:
			return 100_000
		else:
			return 1_000


	def set_appropriate_preresistor(self, current):
		preresistor = self.get_appropriate_preresistor(current)
		self.set_preresistor(preresistor)


	def set_current(self, current):
		excitation = self._calculate_excitation(current)
		self._daq.analog_write(output_channel=0, data=excitation)


	def read_voltage(
		self,
		input_samples,
		input_rate,
		):
		return self._daq.analog_read(0, input_samples, input_rate)


	def measure_resistance(self, current, samples=3000, rate=100000, preresistor=None, gain=None, output_all=False):

		if preresistor is None:
			self.set_appropriate_preresistor(current)
		else:
			self.set_preresistor(preresistor)

		if gain is None:
			self.set_appropriate_gain(current)
		else:
			self.preamplifier.set_gain(gain)

		self.set_current(current)
		x = self.read_voltage(samples, rate)

		df1 = pd.DataFrame(data={
			'time': np.linspace(0, samples/rate, samples),
			'voltage': x,
			'excitation': [self._calculate_excitation(current)]*samples,
			'current': [current]*samples,
			'preresistor': [self.real_preresistor]*samples,
			})

		self.set_current(-current)
		x = self.read_voltage(samples, rate)

		df2 = pd.DataFrame(data={
			'time': np.linspace(0, samples/rate, samples),
			'voltage': x,
			'excitation': [self._calculate_excitation(current)]*samples,
			'current': [-current]*samples,
			'preresistor': [self.real_preresistor]*samples,
			})

		self.set_current(0)

		resistance = (df1['voltage'].mean() - df2['voltage'].mean()) / 2 / current / self.preamplifier.gain
		resistance = np.abs(resistance)

		if output_all:
			return resistance, [df1, df2]
		else:
			return resistance



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

		self.set_current(0)
		self.set_preresistor(preresistor)
		self.preamplifier.set_gain(gain)
		self.set_current(start_current)

		df = self.write_and_measure(
			input_channel=0,
			input_samples=samples,
			input_rate=rate,
			output_channel=0,
			current=measure_current,
		)

		self.set_current(end_current)

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


