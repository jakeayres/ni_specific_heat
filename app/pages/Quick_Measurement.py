import streamlit as st
import matplotlib.pyplot as plt
from ni_specific_heat.ni6003 import Ni6003 


if __name__ == "__main__":

	st.title('Quick Measurement')

	daq = Ni6003()


	fig, ax = plt.subplots(figsize=(12, 7))
	graph = st.pyplot(fig)

	if st.button('Measure'):

		x = daq.analog_read(1, 1000, 1000)
		ax.plot(x)

		with graph:
			st.pyplot(fig)

