import nidaqmx
from nidaqmx.constants import (AcquisitionType, CountDirection, Edge,
    READ_ALL_AVAILABLE, TaskMode, TriggerType)
import pandas as pd
import time
from loguru import logger

from .analog_io import AnalogInput, AnalogOutput
from .digital_io import DigitalOutputGroup



class Ni6003:


	def __init__(self, device_number:int=1):

		system = nidaqmx.system.System.local()
		logger.debug('Loading Ni6003')
		self._device = system.devices[self._device_handle(device_number)]
		logger.debug('Device found')

		self.analog_inputs = self._initialize_analog_inputs()
		self.analog_outputs = self._initialize_analog_outputs()
		self.digital_output_groups = {}


	def _device_handle(self, device_number: int):
		return f'Dev{device_number}'


	def _initialize_analog_outputs(self):
		return [AnalogOutput(self._device, i) for i in range(len(self._device.ao_physical_chans))]


	def _initialize_analog_inputs(self):
		return [AnalogInput(self._device, i) for i in range(len(self._device.ai_physical_chans))]


	def initialize_digital_output_group(self, name, lower_index, upper_index):
		self.digital_output_groups[name] = DigitalOutputGroup(
			device=self._device,
			port_index=0, 
			lower_line_index=lower_index, 
			upper_line_index=upper_index
			)
		logger.debug(f'Digital group created {name}')
		logger.debug(f'{self.digital_output_groups[name]._handle}')


	def digital_write(self, group_name, data):
		self.digital_output_groups[group_name].write(data)


	def analog_read(self, input_channel, samples, rate):

		if rate > 99999:
			rate = 100000
			logger.warning('Maximum rate exceeded. Rate set to 100kHz')
		
		with nidaqmx.Task() as task:
			self.analog_inputs[input_channel].add_to_task(task)
			task.timing.cfg_samp_clk_timing(rate, samps_per_chan=samples)
			return task.read(samples, rate)


	def analog_write(self, output_channel, data):
		with nidaqmx.Task() as task:
			self.analog_outputs[output_channel].add_to_task(task)
			self.analog_write_to_task(task, data)


	def analog_write_to_task(self, task, data):
		try:
			return task.write(data)
		except Exception as e:
			if data >= 10.0:
				logger.warning('Voltage output above allowable limit: +10V set')
				return task.write(10)
			elif data < -10.0:
				logger.warning('Voltage output above allowable limit: -10V set')
				return task.write(-10)
			else:
				return task.write(data)


	def analog_write_and_read(
		self,
		input_channel,
		input_samples,
		input_rate,
		output_channel,
		output_value,
		):
		
		all_data = []

		def callback(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
			nonlocal all_data
			nonlocal input_samples
			nonlocal in_task
			if len(all_data) < input_samples:
				data = in_task.read(number_of_samples_per_channel=number_of_samples)
				all_data.extend(data)
			else:
				pass
			return 0

		if abs(output_value) < 0.5:
			logger.warning(f'Output voltage is very small: {output_value}')


		with nidaqmx.Task() as in_task, nidaqmx.Task() as out_task:
			self.analog_inputs[input_channel].add_to_task(in_task)
			self.analog_outputs[output_channel].add_to_task(out_task)

			in_task.timing.cfg_samp_clk_timing(input_rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=input_samples)
			in_task.register_every_n_samples_acquired_into_buffer_event(1000, callback)

			in_task.start()
			self.analog_write_to_task(out_task, output_value)

			while len(all_data) < input_samples:
				pass

			logger.debug(f'{input_samples} samples acquired')

			return all_data

