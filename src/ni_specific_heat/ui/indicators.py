import dearpygui.dearpygui as gui
from . import Widget



class Indicator(Widget):


	def __init__(self, label, value, unit=None):
		super().__init__()
		self._label = label
		self._value = value
		self._unit = unit


	@classmethod
	def add_to_parent(cls, parent_uuid, label, value, unit=None):
		indicator = cls(label, value, unit)
		gui.add_text(
			tag=indicator.uuid,
			parent=parent_uuid,
			default_value=indicator.display_string,
		)
		return indicator


	@property
	def display_string(self):
		return f'{self.label_string:<16} {self.value_string:>16}  {self.unit_string:<4}'


	@property
	def label_string(self):
		return self._label


	@property
	def value_string(self):
		return f'{self._value}'


	@property
	def unit_string(self):
		return '' if self._unit is None else self._unit


	def set_value(self, value):
		self._value = value
		gui.set_value(item=self.uuid, value=self.display_string)


	def get_value(self):
		return self._value


	def update_callback(self, sender, app_data, user_data):
		self.set_value(user_data)


class DecimalIndicator(Indicator):

	@property
	def value_string(self):
		return f'{self._value:.5f}'



class ScientificDecimalIndicator(Indicator):


	@property
	def value_string(self):
		return f'{self._value:.5E}'


class IntegerIndicator(Indicator):

	@property
	def value_string(self):
		return f'{self._value}'


class BooleanIndicator(Indicator):

	@property
	def value_string(self):
		return f'{self._value}'


