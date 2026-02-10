import asyncio
import numpy as np
import pandas as pd
from loguru import logger
from functools import partial
import dearpygui.dearpygui as gui
import time

from ..ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ..ui.inputs import DecimalInput, IntegerInput, StringInput
from ..ui.plot import Plot

def setup_temp_measure(self):

	temp_window = gui.add_window(label='Temperature', pos=(0, 0), width=300)
	self.live_temperature_plot = Plot.add_to_parent(temp_window, height=200, width=-1)
	gui.add_button(
		parent=temp_window, 
		label='Clear plot', 
		callback=self.live_temperature_plot.clear_all_series,
		)
	self.temperature_indicator = DecimalIndicator.add_to_parent(temp_window, 'Temperature', 0, unit='K')
	self.temperature_rate_indicator = DecimalIndicator.add_to_parent(temp_window, 'Rate', 0, unit='K/min')
	
	gui.add_button(
	    parent=temp_window,
		label='Save data',
		callback=lambda: partial(
			self.queue_temp_measure,
		)
	)
		
	gui.add_button(
		parent=temp_window,
		label='Stop measurement',
		callback=lambda: partial(
			self.stop_temp_measure,
		)
	)

def queue_temp_measure(self):
	self.temp_measure_task = asyncio.create_task(self.measurement_loop(self.data))
	
async def measurement_loop(self,data):
	temp_points = [[], [], []]
	start = time.time()
	while True:
		await asyncio.sleep(1)
		try:
			self.temp_update(data,temp_points)
		except Exception as e:
			logger.error(f"Error in temp measurement: {e}")
	#save data
	temp_points_df = pd.DataFrame({
		'time': temp_points[0],
		'temperature': temp_points[1],
		'rate': temp_points[2]
	})
	temp_points_df.to_csv(f'C://Data/{file_stem}_temp_measurement.csv', index=False, header=['time', 'temperature', 'rate'])

def temp_update(self,data,temp_points):
	temp_points[0].append(time.time() - start)
	temp_points[1].append(data['temperature'])
	temp_points[2].append(data['rate'])


def stop_temp_measure(self):
	task = getattr(self, "_measurement_task", None)
	if task and not task.done():
		task.cancel()
