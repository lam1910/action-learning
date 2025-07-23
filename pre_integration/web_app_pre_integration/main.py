import os

import bcrypt
import psycopg2
import requests
import streamlit as st
from dotenv import load_dotenv

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


# Load database credentials
def load_db_connection(dotenv_path="web_app_pre_integration/.env"):
    load_dotenv(dotenv_path=dotenv_path)

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    return DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def get_connection():
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD = load_db_connection("web_app_pre_integration/.env")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def register_user(user_name, email, password, user_role):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   INSERT INTO "user" (user_name, email, password, user_role)
                   VALUES (%s, %s, %s, %s)
                   """, (user_name, email, hashed, user_role))
    conn.commit()
    cursor.close()
    conn.close()


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
    if 'corrected__class_id' not in st.session_state:
        st.session_state['corrected_class_id'] = 0
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
