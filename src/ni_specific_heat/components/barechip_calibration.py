import pandas as pd
import numpy as np


class BarechipCalibration(object):


	def __init__(self):
		self._dataframe = None
		self._R_to_T_coefficients = None
		self._T_to_R_coefficients = None


	@property
	def dataframe(self):
		""" Pandas dataframe with 'resistance', 'temperature' columns
		"""
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


	def plot_calibration_data(self, plot):
		plot.add_series('calibration', self.dataframe['temperature'].to_numpy(), self.dataframe['resistance'].to_numpy())


	def plot_T_to_R_fit(self, plot):
		x = np.geomspace(self._dataframe['temperature'].min(), self._dataframe['temperature'].max(), 100)
		y = self.evaluate_resistance(x)
		plot.add_line_series('T2R_fit', x, y)


	def plot_R_to_T_fit(self, plot):
		y = np.geomspace(self._dataframe['resistance'].min(), self._dataframe['resistance'].max(), 100)
		x = self.evaluate_temperature(y)
		plot.add_line_series('R2T_fit', x, y)


	def _load_calibration_data(self, sender, app_data, user_data):
		fpath = app_data['file_path_name']

		with open(fpath, 'r') as file:
			s = file.read()
			n_comma = s.count(',')
			n_tab = s.count('\t')

		sep = ',' if n_comma>n_tab else '\t'

		data = pd.read_csv(fpath, sep=sep)
		self._dataframe = data
		
		self.plot_calibration_data(user_data['plot'])
		self.calculate_R_to_T_coefficients()
		self.calculate_T_to_R_coefficients()
		self.plot_T_to_R_fit(user_data['plot'])
		self.plot_R_to_T_fit(user_data['plot'])


	def open_calibration_data_dialog(self, sender, app_data, user_data):
		with gui.file_dialog(
			width=700,
			height=500,
			show=True,
			directory_selector=False,
			callback=self._load_calibration_data,
			user_data=user_data
			):
			gui.add_file_extension(".dat", color=(0, 255, 0, 255), custom_text="[DAT]")
			gui.add_file_extension(".data", color=(0, 255, 0, 255), custom_text="[DATA]")
			gui.add_file_extension(".csv", color=(0, 255, 0, 255), custom_text="[CSV]")
			gui.add_file_extension(".txt", color=(0, 255, 0, 255), custom_text="[TXT]")
			gui.add_file_extension(".*", color=(0, 255, 0, 255), custom_text="[*]")
