# -*- coding: utf-8 -*-
"""stream.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19MGoC3S4IV2oIEU4IOn2lSCYShfqTI7j
"""

import streamlit as st
import fypmodel as model
st.title("Web Based Aspect-based sentiment analysis for earphone and headset")
st.label("Enter the review you want")
input = st.text_input("")
result = model.pipe_lr.predict([input])
st.text(result)