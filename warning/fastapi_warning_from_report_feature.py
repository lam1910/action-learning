from email.mime.multipart import MIMEMultipart

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import psycopg2
from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from urllib.parse import urljoin, urlencode

# just the scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


SQL_WARNING_QUERY = """
with tmp as (
    SELECT COUNT(case when modified_class is not null then 1 end)::FLOAT as modified_prediction
    , (case when COUNT(case when modified_class is null then 1 end) = 0 then 1 else COUNT(case when modified_class is null then 1 end) end)::FLOAT as correct_prediction
    FROM public.past_prediction
    where modified_at >= NOW() - INTERVAL '1 day'
)
select *, modified_prediction / (modified_prediction + correct_prediction) as percentage_modified
from tmp;
"""

# Load database credentials
def load_db_connection(dotenv_path="web_app_pre_integration/.env"):
    load_dotenv(dotenv_path=dotenv_path)

    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    return DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def load_sender_pwd(dotenv_path="web_app_pre_integration/.env"):
    load_dotenv(dotenv_path=dotenv_path)
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    return SENDER_PASSWORD

def get_connection():
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD = load_db_connection("web_app_pre_integration/.env")
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# Email configuration
SENDER = "nguengoclam19@gmail.com"
RECEIVER = "lamnn1910@outlook.com"
SUBJECT = "Please check your Image Classification model"
SENDER_HIDE_EMAIL = "FriendlyBot"

def send_warning_email(sender, sender_password, receiver, subject, body, sender_replace_name=None):
    try:
        # Create the email message
        msg = MIMEText(body)
        msg["Subject"] = subject
        if sender_replace_name is not None:
            msg["From"] = formataddr((sender_replace_name, sender))
        else:
            msg["From"] = sender
        msg["To"] = receiver

        # Send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender, sender_password)  # Use app password if 2FA is enabled
            server.sendmail(sender, receiver, msg.as_string())

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

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

def demo_email_sender_task():
    url = build_url('http://localhost:8000', 'check_model')
    response = requests.get(url)
    if response.status_code // 100 < 4:
        print('DONE!')
    else:
        print(f'ERROR {response.status_code}!')
    print(response.json())

app = FastAPI()
scheduler = BackgroundScheduler()

# Schedule it to run every day at midnight
trigger = IntervalTrigger(minutes=2)
scheduler.add_job(demo_email_sender_task, trigger)
scheduler.start()

@app.get("/check_model")
def email_sender():
    sender_password = load_sender_pwd(dotenv_path="web_app_pre_integration/.env")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(SQL_WARNING_QUERY)
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        modified_prediction, correct_prediction, percentage_modified = result
        all_predictions = modified_prediction + correct_prediction
        is_sent = False
        if percentage_modified >= 0.3:
            msg_body = f"""
Bonjour,

This is a friendly reminder that your model had been flagged {modified_prediction:.0f} time(s), out of {all_predictions:.0f} time(s) in the last day. 
This accounted for {percentage_modified:.4%} unsatisfactory rate. 

Please look at your model. Have a great day!

SIGNED,
FROM YOUR FRIENDLY BOT
"""
            is_sent = send_warning_email(SENDER, sender_password, RECEIVER, SUBJECT, msg_body, SENDER_HIDE_EMAIL)
        return_json = {
            'modified_prediction': modified_prediction,
            'correct_prediction': correct_prediction,
            'percentage_modified': percentage_modified,
            'message_sent': is_sent
        }
        return JSONResponse(return_json, status_code=200)
    else:
        return JSONResponse({'message': 'Not Found'}, status_code=404)
