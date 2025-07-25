import traceback
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin, urlencode

import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

END_POINT = "past_predictions"

st.set_page_config(page_title="Past Predictions", page_icon="📒")
# Date input widgets
st.sidebar.markdown('### Select date range for returning predictions:')
tomorrow = datetime.now() + timedelta(days=1)
min_date = '1990-01-01'
max_date = '2030-12-31'
start_date = st.sidebar.date_input('From', '2025-03-01', min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input('To', tomorrow, min_value=min_date, max_value=max_date)


def build_url(base_url, path='', params=None):
    """
    Constructs a URL with optional path and query parameters.

    :param base_url: The base URL (e.g., 'https://example.com')
    :param path: Optional path to append to the base URL
    :param params: Optional dictionary of query parameters
    :return: Complete URL as a string
    """
    full_url = urljoin(base_url, path)
    if params:
        query_string = urlencode(params)
        full_url = f"{full_url}?{query_string}"
    return full_url


def clicky_link(text, content):
    return f"<a href='{text}' target='_blank'>{content}</a>"


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
        user_id = int(st.session_state['user_id'])
        user_role = 'micro'
        if st.session_state['user_role'] == 'admin':
            user_role = 'admin'
        query_params = {'user_id': user_id, 'user_role': user_role, 'start_date': start_date, 'end_date': end_date}
        url = build_url(base_url, path=END_POINT, params=query_params)
    except KeyError as err:
        st.warning('It seems like you are bypassing the main page. Please return to the main page first')
        url = build_url('http://localhost:8000', END_POINT, params={'user_id': -1, 'user_role': 'k'})
        labels = {-1: 'dummy'}
        st.error(traceback.format_exc())

    try:
        response = requests.get(url)
        result_code = response.status_code
        response_result = response.text
        if result_code // 100 < 4:
            # Wrap the string in a StringIO object
            response_result = StringIO(response_result)
            df_out = pd.read_json(response_result, orient='records')
            if not df_out.empty:
                # Convert 'insertion_timestamp' to datetime
                df_out['insertion_timestamp'] = pd.to_datetime(df_out['insertion_timestamp'])
                df_out['modified_at'] = pd.to_datetime(df_out['modified_at'])
                # Class count
                class_counts = df_out["class_name"].value_counts()
                # count of reported as wrong and good prediction
                reported = df_out["modified_at"].notnull().sum()
                good_pred = df_out["modified_at"].isnull().sum()
                df_out['image_uri'] = df_out.apply(
                    lambda row: clicky_link(
                        row["image_uri"],
                        row["modified_class_name"] if pd.notnull(row["modified_class_name"]) else row["class_name"]
                    ), axis=1
                )
                df_out = df_out.drop(columns=['prediction', 'modified_class'])

                st.markdown("## Detail prediction:")
                st.markdown(
                    df_out.to_html(escape=False, index=False),
                    unsafe_allow_html=True
                )

                st.markdown("## Overview of model performance:")
                # Create columns
                col1, col2 = st.columns(2)

                # 1. Bar Chart: Distribution of Predicted Classes
                with col1:
                    fig1, ax1 = plt.subplots(figsize=(5, 4))
                    class_counts.plot(kind="bar", color="skyblue", ax=ax1)
                    ax1.set_title("Distribution of Predicted Classes")
                    ax1.set_xlabel("Class Name")
                    ax1.set_ylabel("Count")
                    plt.xticks(rotation=45)
                    st.pyplot(fig1)

                # 2. Pie Chart: Reported vs Unreported Predictions
                with col2:
                    fig2, ax2 = plt.subplots(figsize=(5, 4))
                    ax2.pie(
                        [reported, good_pred],
                        labels=["Reported Mistake", "Good Prediction"],
                        autopct="%1.1f%%",
                        colors=["#FF6F61", "#6BAED6"],
                        startangle=140
                    )
                    ax2.set_title("Reported Prediction Ratio")
                    ax2.axis("equal")
                    st.pyplot(fig2)
            else:
                st.warning(
                    f"No prediction found from {start_date} to {end_date} for {st.session_state['user_name']} and the "
                    f"micro-processor"
                )
        else:
            st.error("Request failed")
    except Exception as e:
        st.warning("Server side error. Please contact admin.")
        st.error(e)
