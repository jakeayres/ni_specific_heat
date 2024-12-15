import pandas as pd
import numpy as np


class BarechipCalibration(object):


	def __init__(self):
		self._dataframe = None
		self._R_to_T_coefficients = None
		self._T_to_R_coefficients = None


	@property
	def dataframe(self):
		return self._dataframe


	@property
	def data_loaded(self):
		if self._dataframe is not None:
			return True
		else:
			return False


	@property
	def coefficients_loaded(self):
		if self._R_to_T_coefficients is not None and self._T_to_R_coefficients is not None:
			return True
		else:
			return False


	@property
	def temperature_limits(self):
		return [self._dataframe['temperature'].min(), self._dataframe['temperature'].max()]


	@property
	def resistance_limits(self):
		return [self._dataframe['resistance'].min(), self._dataframe['resistance'].max()]


	def calculate_R_to_T_coefficients(self):
		chebyshev = np.polynomial.chebyshev.Chebyshev.fit(self.dataframe['resistance'].apply(np.log10), self.dataframe['temperature'].apply(np.log10), 9)
		coeffs = chebyshev.convert().coef
		self._R_to_T_coefficients = coeffs


	def calculate_T_to_R_coefficients(self):
		chebyshev = np.polynomial.chebyshev.Chebyshev.fit(self.dataframe['temperature'].apply(np.log10), self.dataframe['resistance'].apply(np.log10), 9)
		coeffs = chebyshev.convert().coef
		self._T_to_R_coefficients = coeffs


	def evaluate_resistance(self, x):
		res = np.polynomial.chebyshev.chebval(np.log10(x), self._T_to_R_coefficients)
		return np.power(10, res)


	def evaluate_temperature(self, x):
		temp = np.polynomial.chebyshev.chebval(np.log10(x), self._R_to_T_coefficients)
		return np.power(10, temp)
