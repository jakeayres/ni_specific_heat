import dearpygui.dearpygui as gui


class Widget(object):


	def __init__(self):
		self._uuid = gui.generate_uuid()


	@property
	def uuid(self):
		return self._uuid
