from loguru import logger
import numpy as np
import pandas as pd
import time
import json
import matplotlib.pyplot as plt
import asyncio
import dearpygui.dearpygui as gui
from functools import partial

from ni_specific_heat.ui.plot import Plot


tasks = []


def setup_gui():
	stage_window = gui.add_window(label='Stage Status', pos=(0, 0), width=300)
	live_temperature_plot = Plot.add_to_parent(stage_window, height=200, width=-1)


	live_temperature_plot.add_series('data', np.random.random(100), np.random.random(100))

	live_temperature_plot.update_series('data', np.random.random(10), np.random.random(10)*10)
	live_temperature_plot.append_series('data', 2+np.random.random(10), 5+np.random.random(10)*2)
	live_temperature_plot.append_series('data', 5+np.random.random(10), 2+np.random.random(10)*5)

	x = live_temperature_plot.get_data('data')


	live_temperature_plot.add_series('data222', np.random.random(100), np.random.random(100))

	live_temperature_plot.update_series('data222', np.random.random(10), np.random.random(10)*10)
	live_temperature_plot.append_series('data222', 2+np.random.random(10), 5+np.random.random(10)*2)
	live_temperature_plot.append_series('data222', 5+np.random.random(10), 2+np.random.random(10)*5)

	x = live_temperature_plot.get_data('data222')

	live_temperature_plot.clear_all_series()


async def _render():
	""" The render loop
	"""
	while gui.is_dearpygui_running():
		gui.render_dearpygui_frame()
		await asyncio.sleep(0.010)
	else:
		gui.destroy_context()


async def _run():
	""" Experiment run loop executing tasks in task queue
	"""
	while True:
		await asyncio.sleep(1)
		try:
			if len(tasks) > 0:
				task = tasks.pop(0)
				await task()
		except Exception as e:
			logger.error('Task raised an exception')
			logger.opt(exception=e).warning("Logging exception traceback")


async def run():
	""" The main asyncio entry point
	"""
	gui.create_context()
	gui.create_viewport(title='Custom Title', width=1100, height=600)
	gui.setup_dearpygui()
	setup_gui()
	gui.show_viewport()
	done, pending = await asyncio.wait(
		[
			asyncio.create_task(_render()),
			asyncio.create_task(_run()),
		],
		return_when=asyncio.FIRST_EXCEPTION,
	)
	gui.destroy_context()


if __name__ == "__main__":
	asyncio.run(run())