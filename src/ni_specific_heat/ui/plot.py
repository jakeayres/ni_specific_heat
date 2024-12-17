import dearpygui.dearpygui as gui
from . import Widget


class Plot(Widget):


	_legend_uuid_suffix = '_legend'
	_x_axis_uuid_suffix = '_x_axis'
	_y_axis_uuid_suffix = '_y_axis'
	_series_uuid_suffix = '_series'


	def __init__(self):
		super().__init__()

		self._series = {}


	def _init_axes(self, xaxis_kwargs={}, yaxis_kwargs={}):
		gui.add_plot_axis(gui.mvXAxis, parent=self.uuid, tag=self.x_axis_uuid, **xaxis_kwargs)
		gui.add_plot_axis(gui.mvYAxis, parent=self.uuid, tag=self.y_axis_uuid, **yaxis_kwargs)


	@classmethod
	def add_to_parent(cls, parent_uuid, xaxis_kwargs={}, yaxis_kwargs={}, **kwargs):
		plot = cls()
		gui.add_plot(
			tag=plot.uuid,
			parent=parent_uuid,
			**kwargs,
		)
		plot._init_axes(xaxis_kwargs, yaxis_kwargs)
		return plot


	@property
	def legend_uuid(self):
		return str(self.uuid) + self._legend_uuid_suffix


	@property
	def x_axis_uuid(self):
		return str(self.uuid) + self._x_axis_uuid_suffix


	@property
	def y_axis_uuid(self):
		return str(self.uuid) + self._y_axis_uuid_suffix


	def series_uuid(self, key):
		return str(self.uuid) + key + self._series_uuid_suffix


	def add_series(self, key, x_data, y_data):

		if key in self._series:
			self.delete_series(key)

		self._series[key] = gui.add_scatter_series(
			x_data,
			y_data,
			parent=self.y_axis_uuid,
			tag=self.series_uuid(key),
			label=key,
			)


	def add_scatter_series(self, key, x_data, y_data):

		if key in self._series:
			self.delete_series(key)

		self._series[key] = gui.add_scatter_series(
			x_data,
			y_data,
			parent=self.y_axis_uuid,
			tag=self.series_uuid(key),
			label=key,
			)


	def add_line_series(self, key, x_data, y_data):

		if key in self._series:
			self.delete_series(key)

		self._series[key] = gui.add_line_series(
			x_data,
			y_data,
			parent=self.y_axis_uuid,
			tag=self.series_uuid(key),
			label=key,
			)


	def update_series(self, key, x_data, y_data):
		gui.set_value(self._series[key], [x_data, y_data])


	def append_series(self, key, x_data, y_data):
		x, y = self.get_data(key)
		gui.set_value(self._series[key], [[*x, *x_data], [*y, *y_data]])


	def get_data(self, key):
		data = gui.get_value(self._series[key])
		return data[0], data[1]


	def delete_series(self, key):
		gui.delete_item(self.series_uuid(key))
		self._series.pop(key, None)


	def clear_series(self, key):
		gui.set_value(self._series[key], [[], []])


	def clear_all_series(self):
		for k, v in self._series.items():
			self.clear_series(k)


	def delete_all_series(self):
		for key, v in self._series.items():
			gui.delete_item(self.series_uuid(key))
		self._series = {}
