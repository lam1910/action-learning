import traceback
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin, urlencode

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


def build_url(base_uri, path='', params=None):
    """
    Constructs a URL with optional path and query parameters.

    :param base_uri: The base URL (e.g., 'https://example.com')
    :param path: Optional path to append to the base URL
    :param params: Optional dictionary of query parameters
    :return: Complete URL as a string
    """
    full_url = urljoin(base_uri, path)
    if params:
        query_string = urlencode(params)
        full_url = f"{full_url}?{query_string}"
    return full_url


def clicky_link(text, content):
    return f"<a href='{text}' target='_blank'>{content}</a>"


END_POINT = "past_predictions"
st.set_page_config(page_title="Overview of the model", page_icon="👩‍🏭")
st.title("📈 Admin Overview Panel")

# Date input widgets
st.sidebar.markdown('### Select date range for returning predictions:')
tomorrow = datetime.now() + timedelta(days=1)
start_of_year = datetime(datetime.now().year, 1, 1)
min_date = '1990-01-01'
max_date = '2030-12-31'
start_date = st.sidebar.date_input('From', start_of_year, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input('To', tomorrow, min_value=min_date, max_value=max_date)

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
            curr_user_id = int(st.session_state['user_id'])
            curr_user_role = st.session_state['user_role']
            query_params = {
                'user_id': curr_user_id,
                'user_role': curr_user_role,
                'start_date': start_date,
                'end_date': end_date
            }
            history_view_url = build_url(base_url, path=END_POINT, params=query_params)
        except KeyError as err:
            st.warning('It seems like you are bypassing the main page. Please return to the main page first')
            history_view_url = build_url('http://localhost:8000', END_POINT, params={'user_id': -1, 'user_role': 'k'})
            labels = {-1: 'dummy'}
            st.error(traceback.format_exc())

        try:
            response = requests.get(history_view_url)
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
                    # daily prediction
                    daily_counts = df_out.groupby(df_out["insertion_timestamp"].dt.date).size().reset_index(
                        name="Count")
                    daily_counts.columns = ["Date", "Predictions"]
                    # Class count
                    class_counts = df_out["class_name"].value_counts().reset_index()
                    class_counts.columns = ["Class", "Count"]
                    # flag error
                    df_out["is_error"] = df_out["modified_at"].isnull()
                    # Group by date
                    error_rate = df_out.groupby(df_out["insertion_timestamp"].dt.date)["is_error"].mean().reset_index()
                    error_rate.columns = ["Date", "Error Rate"]
                    df_out['image_uri'] = df_out.apply(
                        lambda row: clicky_link(
                            row["image_uri"],
                            row["modified_class_name"] if pd.notnull(row["modified_class_name"]) else row["class_name"]
                        ), axis=1
                    )
                    df_out = df_out.drop(columns=['prediction', 'modified_class'])

                    st.markdown("## Overview of model performance:")
                    # chart go here
                    # daily chart
                    fig_daily = px.bar(
                        daily_counts,
                        x="Date",
                        y="Predictions",
                        title="Predictions per Day",
                        labels={"Predictions": "Count"},
                        text_auto=True,
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)

                    # class distribution
                    fig_class = px.pie(
                        class_counts,
                        names="Class",
                        values="Count",
                        title="Class Distribution of Predictions",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    st.plotly_chart(fig_class, use_container_width=True)

                    # error rate
                    fig_error = px.line(
                        error_rate,
                        x="Date",
                        y="Error Rate",
                        markers=True,
                        title="Error Rate Over Time",
                        line_shape="spline",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig_error, use_container_width=True)
                else:
                    st.warning(
                        f"No prediction found from {start_date} to {end_date}"
                    )
            else:
                st.error("Request failed")
        except Exception as e:
            st.warning("Server side error. Please contact admin.")
            st.error(e)
