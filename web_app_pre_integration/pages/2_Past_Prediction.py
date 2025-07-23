import traceback
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin, urlencode

import streamlit as st
import pandas as pd
import requests

END_POINT = "past-predictions"

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


if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("---")
    st.subheader("🔒 Protected Content")
    st.warning('Please go back to main page to login')
else:
    # TODO: Cath load straight to end point (DONE)
    try:
        base_url = st.session_state['base_url']
        labels = st.session_state['labels']
        user_id = int(st.session_state['user_id'])
        user_role = st.session_state['user_role']
        query_params = {'user_id': user_id, 'user_role': user_role}
        url = build_url(base_url, path=END_POINT, params=query_params)
    except KeyError as err:
        st.warning('It seems like you are bypassing the main page. Please return to the main page first')
        url = build_url('http://localhost:8000', END_POINT, params={'user_id': -1, 'user_role': 'k'})
        labels = {-1: 'dummy'}
        st.error(traceback.format_exc())

    # TODO: get data from API and display
    try:
        response = requests.get(url)
        result_code = response.status_code
        response_result = response.text
        if result_code // 100 < 4:
            st.success("Request successful")
            # Wrap the string in a StringIO object
            response_result = StringIO(response_result)
            df_out = pd.read_json(response_result, orient='records')
            list_pred = df_out.loc[:, 'prediction'].to_list()
            list_group = [labels[pred] for pred in list_pred]
            df_out['Class'] = list_group
            # Convert 'insertion_timestamp' to datetime
            df_out['insertion_timestamp'] = pd.to_datetime(df_out['insertion_timestamp'])
            filtered_df = df_out.copy(deep=True)
            # Filter data based on date input
            try:
                filtered_df = filtered_df[(filtered_df['insertion_timestamp'] >= pd.to_datetime(start_date)) & (
                        filtered_df['insertion_timestamp'] <= pd.to_datetime(end_date))]
                filtered_df = filtered_df.reset_index(drop=True)
            except KeyError as k_err:
                st.warning('Something wrong with the output table. Please contact support.')
                st.warning(traceback.format_exc())
            except Exception as err:
                st.warning('Something wrong with the date range. Please check your range or contact support.')
                st.warning(traceback.format_exc())
            st.write(filtered_df)
        else:
            st.error("Request failed")
    except Exception as e:
        st.warning("Server side error. Please contact admin.")
        st.error(e)