import dearpygui.dearpygui as gui
from . import Widget



class Input(Widget):


	def __init__(self, label, value, unit=None):
		super().__init__()
		self._label = label
		self._value = value
		self._unit = unit


	@classmethod
	def add_to_parent(cls, parent_uuid, label, value, unit=None):
		obj = cls(label, value, unit)
		gui.add_input_text(
			tag=obj.uuid,
			parent=parent_uuid,
			label=obj.display_string,
			default_value=obj.value,
			callback=obj._update_value_callback,
		)
		return obj


	def _update_value_callback(self, sender, app_data):
		self.set_value(app_data)


	@property
	def value(self):
		self._value = gui.get_value(item=self.uuid)
		return self._value


	@property
	def label_string(self):
		return self._label


	@property
	def unit_string(self):
		return '' if self._unit is None else f'({self._unit})'


	@property
	def display_string(self):
		return f'{self.label_string} {self.unit_string}'


	def set_value(self, value):
		self._value = value




class IntegerInput(Input):


	@classmethod
	def add_to_parent(cls, parent_uuid, label, value, unit=None):
		obj = cls(label, value, unit)
		gui.add_input_int(
			tag=obj.uuid,
			parent=parent_uuid,
			label=obj.display_string,
			default_value=value,
			callback=obj._update_value_callback,
		)
		return obj


	def set_value(self, value):
		self._value = int(value)


class DecimalInput(Input):


	@classmethod
	def add_to_parent(cls, parent_uuid, label, value, unit=None):
		obj = cls(label, value, unit)
		gui.add_input_double(
			tag=obj.uuid,
			parent=parent_uuid,
			label=obj.display_string,
			default_value=value,
			callback=obj._update_value_callback,
		)
		return obj


	def set_value(self, value):
		self._value = float(value)



class StringInput(Input):


	@classmethod
	def add_to_parent(cls, parent_uuid, label, value, unit=None):
		obj = cls(label, value, unit)
		gui.add_input_text(
			tag=obj.uuid,
			parent=parent_uuid,
			label=obj.display_string,
			default_value=value,
			callback=obj._update_value_callback,
		)
		return obj


	def set_value(self, value):
		self._value = str(value)
