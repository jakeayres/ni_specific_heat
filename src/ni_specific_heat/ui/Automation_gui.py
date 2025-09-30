import asyncio
import numpy as np
import pandas as pd
from loguru import logger
from functools import partial
import dearpygui.dearpygui as gui
import Automation

from ..ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ..ui.inputs import DecimalInput, IntegerInput, StringInput
from ..ui.plot import Plot

def Perform_Automated_Relaxation(experiment, calorimeter_N, file_stem, min_temp, max_temp, plot):
	min_temps =[min_temp]
	max_temps =[min_temp*1.2]
	while max_temps[-1]<(max_temp):
		min_temps.append(min_temps[-1]*1.1)
		max_temps.append(min_temps[-1]*1.2)
	
    min_temps = np.array([min_temps])
    max_temps = np.array([max_temps])
    num_sweeps = len(min_temps)

    relaxation_time_prediction = pd.read_csv('relaxation_time_prediction')   # NEED TO MAKE THIS CSV
    samples = relaxation_time_prediction[0]
    rate = relaxation_time_prediction[1]
    repeats = Automation.generate_repeats(min_temps)
    kappa = pd.read_csv('Thermal_conductance')
    Resistance_values = Automation.R_interpolate(max_temps)
    I = Automation.Relaxation_parameters(min_temps,max_temps,Resistance_values,kappa).generate_currents()

    for i in range(num_sweeps):
        relaxation.perform_relaxation(
	            experiment,
	            calorimeter_N,
                file_stem,
                I[0,i],
                I[1,i],
                samples[i],
                rate[i],
                repeats[i],
                plot)

def setup_Automated_Relaxation(
	experiment,
	):

    window = gui.add_window(label='Perform Automated Relaxation Sweeps', pos=(550, 150), width=550)
	main_plot = Plot.add_to_parent(window, height=400, width=-1)

    columns = gui.add_group(parent=window, horizontal=True, horizontal_spacing=75, width=125)
	left = gui.add_group(parent=columns, width=200)
	right = gui.add_group(parent=columns, width=200)

	calorimeter_N = IntegerInput.add_to_parent(left, 'Calorimeter N', value=0, unit='0/1')
	min_temp = DecimalInput.add_to_parent(left, 'Minimum Temperature', value=1.5, unit='K')
	max_temp = DecimalInput.add_to_parent(left, 'Maximum Temperature', value=30, unit='K')
	
    file_stem = StringInput.add_to_parent(window, 'File stem', value='Relaxations')

	gui.add_button(
		parent=window,
		label='Start Relaxation', 
		callback=lambda: experiment.tasks.append(
			partial(
				Automation.Perform_Automated_Relaxation,
				experiment=experiment,
				calorimeter_N=calorimeter_N.value,
				file_stem=file_stem.value,
				min_temp=min_temp.value
				max_temp=max_temp.value
				plot=main_plot,
			)),
		)