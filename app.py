"""Main web-app entry point. The algebra lab is a supporting workspace."""
from pathlib import Path
import runpy
import streamlit as st

ROOT = Path(__file__).parent

def return_to_study():
    st.session_state.workspace_view = 'Study'

if st.session_state.get('workspace_view') == 'Lab':
    st.sidebar.button('← Back to Phoenix Study', on_click=return_to_study, type='primary')
    runpy.run_path(str(ROOT / 'lab_app.py'), run_name='__main__')
else:
    runpy.run_path(str(ROOT / 'study_app.py'), run_name='__main__')
