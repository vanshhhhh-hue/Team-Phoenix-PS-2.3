"""Main web-app entry point. The algebra lab is a supporting workspace."""
from pathlib import Path
import runpy
import sys
import os
import streamlit as st

ROOT = Path(__file__).parent / 'src' / 'phoenix'
sys.path.insert(0, str(ROOT))

def return_to_study():
    st.session_state.workspace_view = 'Study'

if st.session_state.get('workspace_view') == 'Lab':
    st.sidebar.button('← Back to Phoenix', on_click=return_to_study, type='primary')
    runpy.run_path(str(ROOT / 'lab_app.py'), run_name='__main__')
elif os.getenv('PHOENIX_MODE', 'demo').lower() == 'demo' and st.session_state.get('workspace_view') != 'Uploads':
    runpy.run_path(str(ROOT / 'showcase_app.py'), run_name='__main__')
else:
    if st.session_state.get('workspace_view') == 'Uploads':
        def return_to_physics():
            st.session_state.workspace_view = 'Study'
        st.sidebar.button('← Back to learning workspace', on_click=return_to_physics)
    runpy.run_path(str(ROOT / 'study_app.py'), run_name='__main__')
