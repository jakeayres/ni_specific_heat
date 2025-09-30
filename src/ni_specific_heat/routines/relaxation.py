import asyncio
import numpy as np
import pandas as pd
from loguru import logger
from functools import partial
import dearpygui.dearpygui as gui
from scipy import integrate, interpolate, optimize

from ..ui.indicators import DecimalIndicator, ScientificDecimalIndicator, IntegerIndicator, BooleanIndicator
from ..ui.inputs import DecimalInput, IntegerInput, StringInput
from ..ui.plot import Plot

def calculate_low_current(temperature):
	return 1e-6 * (10 + 0.1*temperature + 0.0005*temperature*temperature)


def calculate_low_preresistor(current):
	pass


def calculate_expected_signal_voltage(current, temperature, calorimeter):
	expected_resistance = calorimeter.calibration.evaluate_resistance(temperature)
	expected_voltage = expected_resistance * current
	return expected_voltage


def calculate_preamplifier_gain(current, temperature, calorimeter):
	voltage = calculate_expected_signal_voltage(current, temperature, calorimeter)
	threshold = 9.8
	if voltage > 10.25:
		logger.warning('Selecting gain: Input saturated at lowest gain.')
		return 1
	elif voltage < 0.0001:
		logger.warning(f'Selecting gain: Small input ({voltage*1000}V) at max gain')
		return 1000
	elif voltage > threshold/10:
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 1')
		return 1
	elif voltage > (threshold/100):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 10')
		return 10
	elif voltage > (threshold/1000):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 100')
		return 100
	elif voltage > (threshold/10000):
		logger.debug(f'{calorimeter._name}: Appropriate gain found: 1000')
		return 1000
	else:
		logger.warning(f'{calorimeter._name}: Gain level not captured in elifs')
		logger.warning(f'{calorimeter._name}: Returning gain level of 1')
		return 1




async def perform_relaxations(
	experiment,
	file_stem,
	minimum_temperature,
	maximum_temperature,
	temperature_steps,
	relaxation_size,
	repeats,
	plot,
	):

	logger.info('Starting relaxations')
	temperatures = np.geomspace(minimum_temperature, maximum_temperature, temperature_steps)

	plot.delete_all_series()

	for temperature in temperatures:

		low_current = calculate_low_current(temperature)
		low_preresistor = experiment.calorimeters[0].calculate_best_preresistor(low_current)
		low_gain = calculate_preamplifier_gain(low_current, temperature, experiment.calorimeters[0])

		high_current = 1e-4
		high_preresistor = experiment.calorimeters[0].calculate_best_preresistor(high_current)
		high_gain = calculate_preamplifier_gain(high_current, temperature, experiment.calorimeters[0])

		logger.info(f'{low_current}, {low_preresistor}, {low_gain}')

		# positive_rising, positive_falling, negative_rising, negative_falling = await experiment.calorimeters[0].measure_sweep(
		# 	low_current=low_current, 
		# 	low_gain=low_gain, 
		# 	low_preresistor=low_preresistor,
		# 	high_current=high_current,
		# 	high_gain=high_gain,
		# 	high_preresistor=high_preresistor,
		# 	rate=90_000,
		# 	samples=90_000,
		# 	plot=plot,
		# )

		positive_rising, positive_falling, negative_rising, negative_falling = await experiment.calorimeters[0].measure_sweep(
			low_current=10e-6, 
			low_gain=10, 
			low_preresistor=100_000,
			high_current=50e-6,
			high_gain=10,
			high_preresistor=100_000,
			rate=90_000,
			samples=10_000,
			plot=plot,
		)


async def perform_relaxation(
	experiment,
	calorimeter_N,
	file_stem,
	low_current,
	high_current,
	samples,
	rate,
	repeats,
	plot,
	):
	logger.info('Performing single relaxation')

	calorimeter = experiment.calorimeters[calorimeter_N]
	preresistor = calorimeter.preresistor.get()
	gain = calorimeter.preamplifier.get()

	for i in range(repeats):

		positive_rising, positive_falling, negative_rising, negative_falling = await calorimeter.measure_sweep(
			low_current=low_current, 
			low_gain=gain, 
			low_preresistor=preresistor,
			high_current=high_current,
			high_gain=gain,
			high_preresistor=preresistor,
			rate=rate,
			samples=samples,
			plot=plot,
		)

		# Save data
		positive_rising.to_csv(f'C://Data/{file_stem}_n_{i}_calorimeter_{calorimeter_N}_positive_rising.dat', index=False)
		positive_falling.to_csv(f'C://Data/{file_stem}_n_{i}_calorimeter_{calorimeter_N}_positive_falling.dat', index=False)
		negative_rising.to_csv(f'C://Data/{file_stem}_n_{i}_calorimeter_{calorimeter_N}_negative_rising.dat', index=False)
		negative_falling.to_csv(f'C://Data/{file_stem}_n_{i}_calorimeter_{calorimeter_N}_negative_falling.dat', index=False)

		averaged_up = pd.DataFrame(data={
			'time': (positive_rising['time']+negative_rising['time']) / 2,
			'voltage': np.abs((positive_rising['voltage']+negative_rising['voltage']) / 2),
			'resistance': np.abs((positive_rising['resistance']+negative_rising['resistance']) / 2),
			})

		plot.add_scatter_series('avg_rising', averaged_up['time'].to_numpy(), averaged_up['resistance'].to_numpy())

		averaged_down = pd.DataFrame(data={
			'time': (positive_falling['time']+negative_falling['time']) / 2,
			'voltage': np.abs((positive_falling['voltage']+negative_falling['voltage']) / 2),
			'resistance': np.abs((positive_falling['resistance']+negative_falling['resistance']) / 2),
			})

		plot.add_scatter_series('avg_falling', averaged_down['time'].to_numpy(), averaged_down['resistance'].to_numpy())


def setup_single_relaxation(
	experiment,
	):

	window = gui.add_window(label='Perform Single Relaxation', pos=(550, 150), width=550)
	main_plot = Plot.add_to_parent(window, height=400, width=-1)

	columns = gui.add_group(parent=window, horizontal=True, horizontal_spacing=75, width=125)
	left = gui.add_group(parent=columns, width=200)
	right = gui.add_group(parent=columns, width=200)

	calorimeter_N = IntegerInput.add_to_parent(left, 'Calorimeter N', value=0, unit='0/1')
	low_current = DecimalInput.add_to_parent(left, 'Low current', value=0.010, unit='mA')
	high_current = DecimalInput.add_to_parent(left, 'High current', value=0.025, unit='mA')

	samples = IntegerInput.add_to_parent(right, 'Samples', value=50000)
	rate = IntegerInput.add_to_parent(right, 'Rate', value=50000, unit='Hz')
	repeats = IntegerInput.add_to_parent(right, 'Repeats', value=5)

	file_stem = StringInput.add_to_parent(window, 'File stem', value='single_relaxation')

	gui.add_button(
		parent=window,
		label='Start relaxation', 
		callback=lambda: experiment.tasks.append(
			partial(
				perform_relaxation,
				experiment=experiment,
				calorimeter_N=calorimeter_N.value,
				file_stem=file_stem.value,
				low_current=low_current.value * 1e-3,
				high_current=high_current.value * 1e-3,
				samples=samples.value,
				rate=rate.value,
				repeats=repeats.value,
				plot=main_plot,
			)),
		)


def setup_relaxations(
	experiment,
	):

	window = gui.add_window(label='Long Relaxation', pos=(550, 150), width=550)
	main_plot = Plot.add_to_parent(window, height=400, width=-1)

	columns = gui.add_group(parent=window, horizontal=True, horizontal_spacing=75, width=125)
	left = gui.add_group(parent=columns, width=200)
	right = gui.add_group(parent=columns, width=200)

	minimum_temperature = DecimalInput.add_to_parent(left, 'T Minimum', value=1.50, unit='K')
	maximum_temperature = DecimalInput.add_to_parent(left, 'T Maximum', value=3.00, unit='K')
	temperature_steps = IntegerInput.add_to_parent(left, 'T Steps', value=2)
	relaxation_size = DecimalInput.add_to_parent(left, 'Relaxation size', value=1.40, unit='x')

	repeats = IntegerInput.add_to_parent(right, 'Repeats', value=5)

	file_stem = StringInput.add_to_parent(window, 'File stem', value='relaxation')

	gui.add_button(
		parent=window,
		label='Start relaxation', 
		callback=lambda: experiment.tasks.append(
			partial(
				perform_relaxations,
				experiment=experiment,
				file_stem=file_stem.value,
				minimum_temperature=minimum_temperature.value,
				maximum_temperature=maximum_temperature.value,
				temperature_steps=temperature_steps.value,
				relaxation_size=relaxation_size.value,
				repeats=repeats.value,
				plot=main_plot,
			)),
		)
	
def Perform_Automated_Relaxation(experiment, calorimeter_N, file_stem, min_temp, max_temp, plot):
	min_temps =[min_temp]
	max_temps =[min_temp*1.2]
	while max_temps[-1]<(max_temp):
		min_temps.append(np.round(min_temps[-1]*1.1,2))
		max_temps.append(np.round(min_temps[-1]*1.2,2))
	
	min_temps = np.array([min_temps])
	max_temps = np.array([max_temps])
	num_sweeps = len(min_temps)
	print(min_temps)
	print(max_temps)

	relaxation_time_prediction = pd.read_csv('automation_csv/relaxation_time_prediction')   # NEED TO MAKE THIS CSV
	samples = relaxation_time_prediction[0]
	rate = relaxation_time_prediction[1]
	kappa = pd.read_csv('automation_csv/Thermal_conductance')
	Resistance_values = R_interpolate(max_temps)
	Relaxation_parameters(min_temps,max_temps,Resistance_values,kappa)
	repeats = Relaxation_parameters().generate_repeats(min_temps)
	I = Relaxation_parameters().generate_currents()

	for i in range(num_sweeps):
	    perform_relaxation(
	            experiment,
	            calorimeter_N,
	            file_stem,
                I[0,i],
                I[1,i],
                samples[i],
                rate[i],
                repeats[i],
                plot)

def setup_automated_relaxation(
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
				Perform_Automated_Relaxation,
				experiment=experiment,
				calorimeter_N=calorimeter_N.value,
				file_stem=file_stem.value,
				min_temp=min_temp.value,
				max_temp=max_temp.value,
				plot=main_plot,
			)),
		)
	

kappa = [[0,1,2,3,4],[0,1,2,3,4]]

def R_interpolate(T_max):
    R_array = pd.read_csv(f'automation_csv/calibration.csv')
    interpolation = interpolate.make_interp_spline(R_array[0], R_array[1])
    R = interpolation(T_max)
    return R

class Relaxation_parameters:

    def  __init__(self,T_min,T_max,R,kappa):
        self.T_max = T_max
        self.T_min = T_min
        self.R = R
        self.I_max = np.empty(len(self.T_min))
        self.I_min = np.empty(len(self.T_min))

    def generate_test_currents(self,est_temps,num_estimations):
        max_est_temps = est_temps*1.25
        self.test_I_max = np.empty(num_estimations)
        self.test_I_min = np.empty(num_estimations)
        for i in range(num_estimations):
            kappa_mask = (kappa[0] >= est_temps[i]) and (kappa[0] <= max_est_temps[i])
            new_kappa = np.array(kappa[0,kappa_mask],kappa[1,kappa_mask])
            self.test_I_min[i] = 0.05
            self.test_I_max[i] = np.sqrt(integrate.simps(new_kappa[1], new_kappa[0])[0]/self.R[i]) + self.test_I_min
        
        return np.array([self.test_I_min,self.test_I_max])

    def generate_currents(self):
        T_min_roll = np.roll(self.T_min,-1)
        N_sweeps = len(self.T_min)
        T_minmax = np.empty(N_sweeps)
        for i in range(N_sweeps):
            min_kappa_mask = (kappa[0] >= self.T_min[i]) and (kappa[0] <= self.T_min[i]+T_minmax[i])
            new_min_kappa = np.array(kappa[0,min_kappa_mask],kappa[1,min_kappa_mask])
            max_kappa_mask = (kappa[0] >= self.T_min[i]) and (kappa[0] <= self.T_max[i])
            new_max_kappa = np.array(kappa[0,max_kappa_mask],kappa[1,max_kappa_mask])
            T_minmax[i] = (self.T_max[i] - T_min_roll[i])/4
            T_minmax[-1] = T_minmax[-2]
            self.I_min[i] = np.sqrt(integrate.simps(new_min_kappa[1], new_min_kappa[0])[0]/self.R[i])
            self.I_max[i] = np.sqrt(integrate.simps(new_max_kappa[1], new_max_kappa[0])[0]/self.R[i]) + self.I_min[i]
        
        #I = np.array([I_max,I_min])

        return np.array([self.I_min,self.I_max])
    
    def test_for_C(self,num_estimations,calorimeter_N,file_stem,samples,rate,repeats):
        self.est_temps = np.linspace(self.T_min[0],self.T_max[-1],num_estimations)
        I_test = Relaxation_parameters(T_min,T_max,R,a,b).generate_test_currents(self.est_temps,num_estimations)
        for n in range(num_estimations):
            perform_relaxation(
	            experiment,
	            calorimeter_N,
                file_stem,
                I_test[0,n],
                I_test[1,n],
                samples,
                rate,
                repeats,
                plot)
            
    def test_fit(x,a,b):
        return a*x + b*x**3
            
    def estimate_C(self,filepath):
        test_data = pd.read_csv(filepath)
        par = scipy.optimize.curve_fit(test_fit,test_data[0],test_data[1])

        return par
    
    def estimate_relaxation_times(self, test_fit_par, T_min, T_max, kappa):
        T_avg = (T_min + T_max)/2
        C_est = test_fit(T_avg,test_fit_par[0],test_fit_par[1])
        interpolation = interpolate.make_interp_spline(kappa[0],kappa[1])
        new_kappa = interpolation(T_avg)
        relaxation_times = 3*(C_est/new_kappa)
        relaxation_time_array = np.ones((2,len(relaxation_times)))
        relaxation_time_array[0] = relaxation_time_array[0]*90000
        relaxation_time_array[1] = relaxation_time_array/relaxation_times
        pd.DataFrame(relaxation_time_array, columns=2)
        pd.DataFrame.to_csv('automation_csv/relaxation_time_prediction.csv')

        return None
    
    def generate_repeats(self,T_min):
        repeats =[]
        for i in range(len(T_min)):
            if T_min[i] < 12:
                repeats.append(5)
            else:
                repeats.append(8)
        return repeats