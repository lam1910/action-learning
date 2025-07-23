import requests
import streamlit as st

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


def authenticate_user(email, password):
    response = requests.post('http://localhost:8000/login', json={'email': email, 'password': password})
    if response.status_code == 200:
        resp = response.json()
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = resp['user_id']
        st.session_state['user_role'] = resp['user_role']
        return {'user_id': resp['user_id'], 'user_name': resp['user_name'], 'user_role': resp['user_role']}
    return None


# Streamlit App
def main():
    # pre setup
    LABELS = {index: key for index, key in enumerate(LABEL)}

    SERVER_URL = "http://127.0.0.1"
    SERVER_PORT = "8000"
    BASE_URL = SERVER_URL + ":" + SERVER_PORT

    # state setup
    if 'labels' not in st.session_state:
        st.session_state['labels'] = LABELS
    if 'base_url' not in st.session_state:
        st.session_state['base_url'] = BASE_URL
    if 'corrected_class_name' not in st.session_state:
        st.session_state['corrected_class_name'] = 'other'
    if "report_comment" not in st.session_state:
        st.session_state['report_comment'] = ""
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = 0
    if 'user_role' not in st.session_state:
        st.session_state['user_role'] = 'k'
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_name' not in st.session_state:
        st.session_state['user_name'] = ""

    # page setup
    st.set_page_config(page_title="Sign In", page_icon="🔐", layout="centered")
    st.title("🔐 Sign In")
    st.sidebar.success("Select your usage above.")

    st.markdown(
        """
        This is the home page of our micro-processor demo app

        **👈 Select a demo from the sidebar** to see some use cases
        of our app!
    """
    )

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign In"):
        user = authenticate_user(email, password)
        if user:
            st.success(f"Welcome, {user['user_name']}! (Role: {user['user_role']})")
            st.session_state.logged_in = True
            st.session_state.user_id = user['user_id']
            st.session_state.user_role = user['user_role']
            st.session_state.user_name = user['user_name']
        else:
            st.error("Invalid email or password.")
            st.session_state.logged_in = False

    if st.session_state.get("logged_in"):
        st.markdown("---")
        st.subheader("🔓 Protected Content")
        st.write(f"Hello **{st.session_state['user_name']}**, you are logged in.")


if __name__ == "__main__":
    main()
