import numpy as np
import scipy.integrate as integrate
from Auto_calibration_R import R_interpolate
import pandas as pd
import csv
import scipy.interpolate as interpolate
import scipy.optimize
import relaxation
import CpExperiment


T_min = np.array([1.5,2.3,2.8,3.2,3.8,4.5,5.5,6.5,7.6,9.25])
T_max = np.array([2.5,2.9,3.3,4.0,4.9,6.2,7.0,8.2,9.8,11.0])
N_sweeps = len(T_min)
T_minmax = np.zeros(N_sweeps)
R = np.ones(N_sweeps)

def abs_min():
    return 1.5

def kappa(x,a,b):
    return a+b

a=1
b=0

experiment = CpExperiment()

x_par = np.arange(0.1,5.1,0.1)

def logar(x):
    return 10**(-x)

y_par = logar(x_par)

def R_interpolate(T_max):
    R_array = pd.read_csv(f'calibration.csv')
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
            relaxation.perform_relaxation(
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

        return relaxation_times
    
    def generate_repeats(self,T_min):
        repeats =[]
        for i in range(len(T_min)):
            if T_min[i] < 12:
                repeats.append(5)
            else:
                repeats.append(8)
        return repeats


        

I = Relaxation_parameters(T_min,T_max,R,a,b).generate_currents()
print(I)

