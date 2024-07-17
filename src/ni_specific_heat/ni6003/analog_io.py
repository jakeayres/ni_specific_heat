class AnalogInput:


	def __init__(self, device, input_number):
		self._handle = f'{device.name}/ai{input_number}'

		self.minimum_rate = device.ai_min_rate
		self.maximum_rate = device.ai_max_multi_chan_rate
		self.minimum_value = device.ai_voltage_rngs[0]
		self.maxmimum_value = device.ai_voltage_rngs[1]


	def add_to_task(self, task):
		task.ai_channels.add_ai_voltage_chan(self._handle)


class AnalogOutput:


	def __init__(self, device, output_number):
		self._handle = f'{device.name}/ao{output_number}'

		self.minimum_rate = device.ao_min_rate
		self.maximum_rate = device.ao_max_rate
		self.minimum_value = device.ao_voltage_rngs[0]
		self.maxmimum_value = device.ao_voltage_rngs[1]


	def add_to_task(self, task):
		task.ao_channels.add_ao_voltage_chan(self._handle)