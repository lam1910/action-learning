import streamlit as st

st.set_page_config(
    page_title='Micro Processor Demo',
    page_icon='👋',
)

st.write("# Welcome to Our Demo in Micro Processor! 👋")

st.sidebar.success("Select your usage above.")

st.markdown(
    """
    This is the home page of our micro-processor demo app
    
    **👈 Select a demo from the sidebar** to see some use cases
    of our app!
"""
)

LABEL = [
    'airplane',
    'automobile',
    'bird',
    'cat',
    'deer',
    'dog',
    'frog',
    'horse',
    'ship',
    'truck',
    'other'
]

LABELS = {index: key for index, key in enumerate(LABEL)}

SERVER_URL = "http://127.0.0.1"
SERVER_PORT = "8000"
BASE_URL = SERVER_URL + ":" + SERVER_PORT

if 'labels' not in st.session_state:
    st.session_state['labels'] = LABELS
if 'base_url' not in st.session_state:
    st.session_state['base_url'] = BASE_URL
if 'corrected__class_id' not in st.session_state:
    st.session_state['corrected_class_id'] = 0
if "report_comment" not in st.session_state:
    st.session_state['report_comment'] = ""
