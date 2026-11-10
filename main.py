"""TerraPulse: one app, two tools.  Run with:  streamlit run main.py"""

import streamlit as st

from terrapulse import ui

st.set_page_config(page_title="TerraPulse", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

ui.inject_css()   # shared design system for both pages

pages = [
    st.Page("views/detective.py", title="Trend Detective", icon=":material/travel_explore:", default=True),
    st.Page("app.py", title="Risk Lab: drought & fire", icon=":material/local_fire_department:"),
]
st.navigation(pages).run()
