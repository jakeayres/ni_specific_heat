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

	temp_window = gui.add_window(label='Temperature Measurement', pos=(550, 150), width=300)
	self.temperature_indicator = DecimalIndicator.add_to_parent(temp_window, 'Temperature', 0, unit='K')
	self.temperature_rate_indicator = DecimalIndicator.add_to_parent(temp_window, 'Rate', 0, unit='K/min')
	self.filename = StringInput.add_to_parent(temp_window, 'Filename', 'temperature_measurements', unit=None)
	
	gui.add_button(
	    parent=temp_window,
		label='Start measurement',
		callback=lambda:
			queue_temp_measure(self),
		
	)
		
	gui.add_button(
		parent=temp_window,
		label='Stop measurement',
		callback=lambda:
			stop_temp_measure(self),
		
	)

async def measurement_loop(self,temperature_indicator,temperature_rate_indicator):
	logger.info("Starting temperature measurement loop")
	self.temp_points = [[], [], []]
	start = time.time()
	while True:
		await asyncio.sleep(1)
		try:
			temp_update(self,temperature_indicator,temperature_rate_indicator,self.temp_points,start)
		except Exception as e:
			logger.error(f"Error in temp measurement: {e}")


def save_temp_measurement(self, temp_points, filestem):
	temp_points_df = pd.DataFrame({
		'time': temp_points[0],
		'temperature': temp_points[1],
		'rate': temp_points[2]
	})
	print(temp_points_df)
	temp_points_df.to_csv(rf'C:\Data\Charlie_Hannah\temperature_measurements\{filestem}.csv', index=False, header=['time', 'temperature', 'rate'])

def queue_temp_measure(self):
	if getattr(self, "_temp_task", None):
		logger.warning("Measurement already running")
		return

	logger.info("Queueing temperature measurement task")
	asyncio.set_event_loop(self.loop)
	self._temp_task = self.loop.create_task(
    	    measurement_loop(
    	        self,
    	        self.temperature_indicator,
    	        self.temperature_rate_indicator,
    	    )
    	)	
	logger.info("Temperature measurement started")


def temp_update(self,temperature_indicator,temperature_rate_indicator,temp_points,start):
	temp_points[0].append(time.time() - start)
	temp_points[1].append(temperature_indicator._value)
	temp_points[2].append(temperature_rate_indicator._value)
	logger.debug(f"Temp update: {temp_points[0][-1]:.2f}s, {temp_points[1][-1]:.2f}K, {temp_points[2][-1]:.2f}K/min")

def stop_temp_measure(self):
	filestem = f"{self.filename._value}_{time.strftime('%Y_%m_%d_%H_%M')}"
	task = getattr(self, "_temp_task", None)
	if task and not task.done():
		self._temp_task.cancel()
		save_temp_measurement(self, self.temp_points, filestem)
		logger.info("Temperature measurement stopped and data saved")
		self._temp_task = None
