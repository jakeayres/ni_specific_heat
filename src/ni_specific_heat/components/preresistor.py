import pandas as pd
import numpy as np
from loguru import logger



class Resistor:

	def __init__(
		self,
		daq,
		nominal_resistance,
		real_resistance,
		digital_group_name,
		digital_group_config,
		):

		self._daq = daq
		self._digital_group_name = digital_group_name
		self._digital_group_config = digital_group_config
		self._nominal_resistance = nominal_resistance
		self._real_resistance = real_resistance


	def set(self):
		self._daq.digital_output_groups[self._digital_group_name].write(self._digital_group_config)


	@property
	def nominal_resistance(self):
		return self._nominal_resistance


	@property
	def real_resistance(self):
		return self._real_resistance
	


class Preresistor:


	def __init__(
		self,
		daq,
		key: str,
		digital_lines={'K0': 4, 'K1': 5},
		):

		self._daq = daq
		self._key = key
		self._digial_lines = digital_lines
		self._daq.initialize_digital_output_group(self._key, min(digital_lines.values()), max(digital_lines.values()))

		self._resistors = {}
		self._active_resistor = None


	def add_resistor(
		self,
		nominal_resistance,
		real_resistance,
		config,
		set_resistor: bool = False,
		):

		self._resistors[nominal_resistance] = Resistor(
			daq=self._daq,
			nominal_resistance=nominal_resistance,
			real_resistance=real_resistance,
			digital_group_name=f'{self._key}',
			digital_group_config=config,
			)

		if set_resistor:
			self._active_resistor = self._resistors[nominal_resistance]
			self._active_resistor.set()
			logger.debug(f'Preresistor set {nominal_resistance}')


	def set(self, resistance, callback=None):
		if resistance == self._active_resistor.nominal_resistance:
			logger.debug(f'Preresistor already set to {resistance}')
			return self._active_resistor.real_resistance
		else:
			self._active_resistor = self._resistors[resistance]
			self._active_resistor.set()
			logger.debug(f'Preresistor set to {resistance}')
			return self._active_resistor.real_resistance


	def get(self):
		return self._active_resistor.real_resistance


	@property
	def nominal_resistance(self):
		return self._active_resistor.nominal_resistance


	@property
	def real_resistance(self):
		return self._active_resistor.real_resistance