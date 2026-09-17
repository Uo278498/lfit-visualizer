"""Punto de entrada de la aplicación LFIT Visualizer."""

import streamlit as st

from src.state import initialize_session_state
from views import configuration, data, export, preprocessing, results, variables


st.set_page_config(page_title="LFIT Visualizer", page_icon="🧠", layout="wide")
initialize_session_state(st.session_state)

PAGES = {
    "1. Datos": data.render,
    "2. Variables": variables.render,
    "3. Preprocesar y discretizar": preprocessing.render,
    "4. Configurar": configuration.render,
    "5. Resultados": results.render,
    "6. Exportar": export.render,
}

st.sidebar.title("LFIT Visualizer")
section = st.sidebar.radio("Flujo de trabajo", list(PAGES))
st.sidebar.caption("Prototipo experimental · PRIDE integrado en modo estático")

PAGES[section]()
