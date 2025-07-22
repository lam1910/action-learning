import traceback

import numpy as np
import streamlit as st
import requests
import pandas as pd
from urllib.parse import urlencode, urlunparse
import json
import base64


from PIL import Image

END_POINT = "predict"

st.set_page_config(page_title="Predict (User Input)", page_icon="✍️")

def upload_image():
    img = st.file_uploader("Upload an image", type=["csv", "png"])
    return img

def parse_img(uploaded_img):
    # TODO: actual code to parse an image to API
    base64_img = base64.b64encode(uploaded_img.read()).decode("utf-8")
    # Convert the image to a NumPy array
    # image_array = np.array(image)
    return base64_img

def submit_on_click():
    corrected_class = labels[st.session_state.corrected_class_id]
    # TODO: Save report to DB or send to server
    st.success(f"Thank you! You reported the correct class as **{corrected_class}**.")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("---")
    st.subheader("🔓 Protected Content")
    st.warning('Please go back to main page to login')
else:
    # TODO: Cath load straight to end point (DONE)
    try:
        base_url = st.session_state['base_url']
        labels = st.session_state['labels']
        url = base_url + "/" + END_POINT
    except KeyError as err:
        st.warning('It seems like you are bypassing the main page. Please return to the main page first')
        url = 'http://localhost:8000' + "/" + END_POINT
        labels = {-1: 'dummy'}
        st.error(traceback.format_exc())

    # TODO: Upload button (DONE)
    uploaded_img = upload_image()

    # TODO: catch not image
    if uploaded_img:
        st.text("Your uploaded image:")
        st.image(uploaded_img, use_container_width=True)
        # TODO: Feed to API (DONE)
        if st.button("Predict"):
            # TODO: should change -1 to actual user_id and role once the sign in is up
            payload = {'user_id': -1, 'user_role': -1, 'image': parse_img(uploaded_img)}
            response = requests.post(url, data=json.dumps(payload))
            if response.status_code // 100 < 4:
                st.success("Your image was successfully parsed and sent to the API!")
                result = response.json()
                # result = {'results': [{'prediction_id': 1, 'prediction': 1}]}
                img_class = [labels[result['prediction']] for result in result['results']]
                st.text(f"Your classification result: {img_class[0]}")
            else:
                st.error("Prediction failed")
            # TODO: Report Button
            st.markdown("### 📝 Do we make a mistake. Report a Correction")
            with st.form('my_form'):
                idx = st.number_input('Class Id', min_value=0, max_value=11, step=1, key='corrected_class_id')
                st.text_area("Optional comment", key="report_comment")

                # Every form must have a submit button
                # TODO: modifying on_click behaviour
                submitted = st.form_submit_button('Submit', on_click=submit_on_click)
                cancelled = st.form_submit_button('Cancel')
