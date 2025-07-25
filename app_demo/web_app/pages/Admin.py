import re
import traceback

import requests
import streamlit as st


def is_valid_email(email_looking_string):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email_looking_string)


END_POINT = "register"
ACCEPTED_ROLE = ["admin", "user", "data-engineer", "data-analyst", "data-scientist", "embedding-engineer", "micro"]
st.set_page_config(page_title="Add New User", page_icon="👩‍🏭")
st.title("🔐 Admin Register Panel")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = 'user'

if not st.session_state.logged_in:
    st.markdown("---")
    st.subheader("🔒 Protected Content")
    st.warning('Please go back to main page to login')
else:
    if st.session_state['user_role'] != 'admin':
        st.markdown("---")
        st.subheader("🔒 Admin Content")
        st.error('You do not have permission to access this page')
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
        # User input form
        with st.form("add_user_form"):
            user_name = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            user_role = st.selectbox("User Role", ACCEPTED_ROLE)

            submitted = st.form_submit_button("Register User")

            if submitted:
                if not is_valid_email(email):
                    st.error("🚫 Invalid email format.")
                else:
                    new_user_data = {
                        "user_name": user_name,
                        "email": email,
                        "password": password,
                        "user_role": user_role
                    }
                    try:
                        response = requests.post(url, json=new_user_data)
                        if response.status_code == 200:
                            st.success("✅ User registered successfully!")
                        else:
                            st.error(f"❌ Failed to register user: {response.json().get('detail')}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"🌐 Connection error: {e}")
