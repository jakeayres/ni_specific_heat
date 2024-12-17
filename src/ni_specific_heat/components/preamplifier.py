import pandas as pd
import numpy as np
from loguru import logger


class Preamplifier:


	def __init__(
		self,
		daq,
		key: str,
		digital_lines={'A0': 2, 'A1': 3, 'WR': 0},
		):

		self._daq = daq
		self._key = key
		self._digial_lines = digital_lines
		self._daq.initialize_digital_output_group(self._key, min(digital_lines.values()), max(digital_lines.values()))
		self.gain = None
		self._callbacks = []
		
		self.set(1)



	def add_callback(self, callback):
		self._callbacks.append(callback)


	def _run_callbacks(self, value):
		for callback in self._callbacks:
			callback(value)


	def _make_boolean_list(self, config_dict):
		min_index = min(self._digial_lines.values())
		max_index = max(self._digial_lines.values())
		result = []
		
		for i in range(min_index, max_index + 1):
			found = False
			for key, value in self._digial_lines.items():
				if value == i:
					result.append(config_dict.get(key, False))
					found = True
					break
			if not found:
				result.append(False)

		return result


	def _set_gain_1(self, callback=None):
		line_1 = {'WR': True, 'A1': False, 'A0': False}
		line_2 = {'WR': False, 'A1': False, 'A0': False}
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_1))
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_2))
		self.gain = 1
		if callback is not None:
			callback(self.gain)
		self._run_callbacks(self.gain)


	def _set_gain_10(self, callback=None):
		line_1 = {'WR': True, 'A1': True, 'A0': False}
		line_2 = {'WR': False, 'A1': True, 'A0': False}
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_1))
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_2))
		self.gain = 10
		if callback is not None:
			callback(self.gain)
		self._run_callbacks(self.gain)


	def _set_gain_100(self, callback=None):
		line_1 = {'WR': True, 'A1': False, 'A0': True}
		line_2 = {'WR': False, 'A1': False, 'A0': True}
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_1))
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_2))
		self.gain = 100
		if callback is not None:
			callback(self.gain)
		self._run_callbacks(self.gain)


	def _set_gain_1000(self, callback=None):
		line_1 = {'WR': True, 'A1': True, 'A0': True}
		line_2 = {'WR': False, 'A1': True, 'A0': True}
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_1))
		self._daq.digital_output_groups[self._key].write(self._make_boolean_list(line_2))
		self.gain = 1000
		if callback is not None:
			callback(self.gain)
		self._run_callbacks(self.gain)


	def set(self, gain, callback=None):
		if gain != self.gain:
			if gain == 1:
				self._set_gain_1(callback=callback)
				logger.debug(f'Gain changed: {gain}')
			elif gain == 10:
				self._set_gain_10(callback=callback)
				logger.debug(f'Gain changed: {gain}')
			elif gain == 100:
				self._set_gain_100(callback=callback)
				logger.debug(f'Gain changed: {gain}')
			elif gain == 1000:
				self._set_gain_1000(callback=callback)
				logger.debug(f'Gain changed: {gain}')
			else:
				logger.warning(f'Gain not changed: {gain} not an allowed value.')
		else:
			logger.debug(f'Gain not changed: gain already at value.')


	def get(self, callback=None):
		if callback is not None:
			callback(self.gain)
		self._run_callbacks(self.gain)
		return self.gain

