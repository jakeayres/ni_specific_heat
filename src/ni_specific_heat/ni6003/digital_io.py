import nidaqmx
from nidaqmx.constants import LineGrouping


class DigitalOutputGroup:

	def __init__(self, device, port_index, lower_line_index, upper_line_index):
		self._handle = f'{device.name}/port0/line{lower_line_index}:{upper_line_index}'


	def add_to_task(self, task):
		task.do_channels.add_do_chan(self._handle, line_grouping=LineGrouping.CHAN_PER_LINE)


	def write(self, data:list[bool]):
		with nidaqmx.Task() as task:
			task.do_channels.add_do_chan(self._handle, line_grouping=LineGrouping.CHAN_PER_LINE)
			task.start()
			task.write(data)
			task.stop()