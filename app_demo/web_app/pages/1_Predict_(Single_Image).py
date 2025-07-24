import base64
import traceback

import requests
import streamlit as st

END_POINT = "predict"

st.set_page_config(page_title="Predict (User Input)", page_icon="🫵")


def upload_image():
    img = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    return img


def parse_img(load_img):
    base64_img = base64.b64encode(load_img.read()).decode("utf-8")
    return base64_img


def submit_on_click(prediction_id):
    correct_class_name = st.session_state["corrected_class_name"]
    corrected_class_id = [key for key, val in labels.items() if val == correct_class_name][0]

    # id of db start at 1
    report_payload = {
        "prediction_id": prediction_id,
        "correct_class_id": corrected_class_id + 1,
        "correct_class_name": correct_class_name
    }

    try:
        report_response = requests.post("http://localhost:8000/report_mistake", json=report_payload)
        if report_response.status_code // 100 < 4:
            st.success(f"Thank you! You reported the correct class as **{correct_class_name}**.")
        else:
            st.error(f"Server responded with status code {report_response.status_code}.")
    except Exception as e:
        st.error(f"Failed to report correction: {e}")


if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("---")
    st.subheader("🔒 Protected Content")
    st.warning('Please go back to main page to login')
else:
    try:
        base_url = st.session_state['base_url']
        labels = st.session_state['labels']
        url = base_url + "/" + END_POINT
    except KeyError as err:
        st.warning('It seems like you are bypassing the main page. Please return to the main page first')
        url = 'http://localhost:8000' + "/" + END_POINT
        labels = {-1: 'dummy'}
        st.error(traceback.format_exc())

    pred_id = 0
    uploaded_img = upload_image()

    if uploaded_img:
        st.text("Your uploaded image:")
        st.image(uploaded_img, use_container_width=True)
        if st.button("Predict"):
            predict_payload = {'user_id': st.session_state['user_id'], 'user_role': st.session_state['user_role'],
                               'image': parse_img(uploaded_img)}
            response = requests.post(url, json=predict_payload)
            if response.status_code // 100 < 4:
                st.success("Your image was successfully parsed and sent to the API!")
                result = response.json()
                img_result = [(result['prediction_id'], labels[result['prediction']]) for result in result['results']]
                pred_id, img_class = img_result[0]
                st.text(f"Your classification result: {img_class}")
            else:
                st.error("Prediction failed")
            st.markdown("### 📝 Do we make a mistake. Report a Correction")
            with st.form('my_form'):
                corrected_class_name = st.selectbox('Corrected Class', labels.values(), key='corrected_class_name')
                st.text_area("Optional comment", key="report_comment")

                # Every form must have a button to submit
                submitted = st.form_submit_button('Submit', on_click=submit_on_click, kwargs={'prediction_id': pred_id})
                cancelled = st.form_submit_button('Cancel')
