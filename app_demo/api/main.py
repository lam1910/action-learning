import base64
import io
import os
import smtplib
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any
from urllib.parse import urljoin, urlencode

import bcrypt
import cloudinary
import cloudinary.api
import cloudinary.uploader
import psycopg2
import requests
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
# just the scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.extras import DictCursor
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse
from torchvision import models
from torchvision import transforms

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

SQL_WARNING_QUERY = """with tmp as (
    SELECT COUNT(case when modified_class is not null then 1 end)::FLOAT as modified_prediction
    , (case when COUNT(case when modified_class is null then 1 end) = 0 then 1 else COUNT(case when modified_class is null then 1 end) end) ::FLOAT as correct_prediction
    FROM public.past_prediction
    where modified_at >= NOW() - INTERVAL '1 day' OR (modified_at is null and insertion_timestamp >= NOW() - INTERVAL '1 day')
    )
select *, modified_prediction / (modified_prediction + correct_prediction) as percentage_modified
from tmp;"""

# Email configuration
SENDER = "nguengoclam19@gmail.com"
RECEIVER = "lamnn1910@outlook.com"
SUBJECT = "Please check your Image Classification model"
SENDER_HIDE_EMAIL = "FriendlyBot"


# Define your custom MobileNetV3 class
class MobileNetV3(nn.Module):
    def __init__(self):
        super(MobileNetV3, self).__init__()
        self.model = models.mobilenet_v3_small(pretrained=True)
        self.model.classifier[3] = nn.Linear(1024, 10)
        self.freeze()

    def forward(self, x):
        if x.shape[2:] != (224, 224):
            x = F.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
        return self.model(x)

    def freeze(self):
        for param in self.model.parameters():
            param.requires_grad = False
        for param in self.model.classifier[3].parameters():
            param.requires_grad = True

    def unfreeze(self):
        for param in self.model.parameters():
            param.requires_grad = True


# Instantiate and load weights with error handling
base_dir = os.path.dirname(__file__)
model_path = os.path.join(base_dir, "models", "mobilenet_transfer_v1_model.pth")
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file {model_path} not found")
model = MobileNetV3()
model.load_state_dict(torch.load(model_path, map_location='cpu'))
model.eval()

transform = transforms.Compose([
    transforms.Resize((32, 32)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
])


def load_config(dotenv_path=None):
    if dotenv_path is None:
        curr_path = os.path.dirname(__file__)
        dotenv_path = os.path.join(curr_path, ".env")
    load_dotenv(dotenv_path=dotenv_path)

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    cloud_name = os.getenv("CLOUD_NAME")
    cloud_key = os.getenv("CLOUD_KEY")
    cloud_secret = os.getenv("CLOUD_SECRET")
    sender_password = os.getenv("SENDER_PASSWORD")
    return db_host, db_port, db_name, db_user, db_password, cloud_name, cloud_key, cloud_secret, sender_password


def get_connection():
    db_host, db_port, db_name, db_user, db_password, _, _, _, _ = load_config()
    return psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password
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


def upload_image_to_cloudinary(cloud_name, api_key, api_secret, image_bytes):
    unique_name = f"predictions/{uuid.uuid4()}"
    result = cloudinary.uploader.upload(
        image_bytes,
        public_id=unique_name,
        resource_type="image",
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    # The public URL of the uploaded image
    return result['secure_url']


class RegisterRequest(BaseModel):
    user_name: str
    email: EmailStr
    password: str
    user_role: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PredictRequest(BaseModel):
    user_id: int
    user_role: str
    image: Any


class PredictionInput(BaseModel):
    user_id: int
    prediction_id: int
    # image: Any # Scrapped because of the microprocessor is too weak


class CorrectionRequest(BaseModel):
    prediction_id: int
    correct_class_id: int
    correct_class_name: str


def predict(image_b64: str) -> tuple[bytes, int | float | bool]:
    image_data = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    image = transform(image)
    input_tensor = image.unsqueeze(0)  # Add batch dimension

    with torch.no_grad():
        output = model(input_tensor)
        prediction = torch.argmax(output, dim=1).item()

    return image_data, prediction


def log_prediction(user_id: int, image_uri: str, prediction: int, class_name: str = None) -> int:
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    '''
                    INSERT INTO past_prediction (user_id, image_uri, prediction, class_name)
                    VALUES (%s, %s, %s, %s) RETURNING prediction_id
                    ''',
                    (user_id, image_uri, prediction, class_name)
                )
                result = cursor.fetchone()
                conn.commit()
                return result["prediction_id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logging error: {str(e)}")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/login")
async def login_user(credentials: LoginRequest):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    'SELECT user_id, user_name, password, user_role FROM "user" WHERE email = %s',
                    (credentials.email,)
                )
                user = cursor.fetchone()
                if user:
                    user_id, user_name, hashed_password, user_role = user
                    if bcrypt.checkpw(credentials.password.encode('utf-8'), hashed_password.encode('utf-8')):
                        json_out = {"user_id": user["user_id"], "user_name": user["user_name"],
                                    "user_role": user["user_role"]}
                        return json_out
                    else:
                        raise HTTPException(status_code=401, detail="Invalid email or password")
                else:
                    raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")


@app.post("/predict")
async def predict_handler(predict_payload: PredictRequest):
    # Step 1: Make prediction
    img_data, prediction = predict(predict_payload.image)

    # Optional: Map prediction ID to a human-readable class name (if you’ve got a class map)
    # e.g., class_name = class_lookup[prediction]
    class_name = LABEL[prediction]  # or set dynamically if needed

    # Step 2: Log the prediction into the database
    # Assume you generate or retrieve image_uri somewhere (local path, S3 link, etc.)
    _, _, _, _, _, cloud_name, cloud_api, cloud_secret, _ = load_config()
    img = io.BytesIO(img_data)
    image_uri = upload_image_to_cloudinary(cloud_name, cloud_api, cloud_secret, img)

    # index in db start at 1
    prediction_id = log_prediction(
        user_id=predict_payload.user_id,
        image_uri=image_uri,
        prediction=prediction + 1,
        class_name=class_name
    )

    # Step 3: Return response
    return {
        "results": [
            {
                "prediction_id": prediction_id,
                "prediction": prediction
            }
        ]
    }


@app.post("/report_mistake")
async def report_mistake(report_payload: CorrectionRequest):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    '''
                    UPDATE past_prediction
                    SET modified_class      = %s,
                        modified_class_name = %s,
                        modified_at         = now()
                    WHERE prediction_id = %s
                    ''',
                    (report_payload.correct_class_id, report_payload.correct_class_name, report_payload.prediction_id)
                )
                conn.commit()
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating prediction: {str(e)}")


@app.get("/past_predictions")
async def get_past_predictions(user_id: int = Query(...), user_role: str = Query(...), start_date: str = Query(...),
                               end_date: str = Query(...)):
    try:
        with get_connection() as conn:
            actual_start_date = datetime.strptime(start_date, '%Y-%m-%d')
            actual_end_date = datetime.strptime(end_date, '%Y-%m-%d')
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                if user_role.lower() == "admin":
                    query = '''
                            SELECT pp.prediction_id,
                                   pp.user_id,
                                   pp.image_uri,
                                   pp.prediction,
                                   pp.class_name,
                                   pp.insertion_timestamp,
                                   pp.modified_class,
                                   pp.modified_class_name,
                                   pp.modified_at
                            FROM past_prediction pp
                            WHERE pp.insertion_timestamp BETWEEN %s AND %s
                            ORDER BY pp.insertion_timestamp DESC \
                            '''
                    params = (actual_start_date, actual_end_date)
                else:
                    query = '''
                        SELECT pp.prediction_id,
                               pp.user_id,
                               pp.image_uri,
                               pp.prediction,
                               pp.class_name,
                               pp.insertion_timestamp,
                               pp.modified_class,
                               pp.modified_class_name,
                               pp.modified_at
                        FROM past_prediction pp
                                 JOIN "user" u ON pp.user_id = u.user_id
                        WHERE pp.insertion_timestamp between %s AND %s
                          AND (pp.user_id = %s
                            OR u.user_role = %s)
                        ORDER BY pp.insertion_timestamp DESC
                        '''
                    params = (actual_start_date, actual_end_date, user_id, user_role)
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching past predictions: {str(e)}")


@app.get("/check_model")
def email_sender():
    _, _, _, _, _, _, _, _, sender_password = load_config()
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


@app.post("/submit_prediction/")
def submit_prediction(mcr_proc_data: PredictionInput):
    fixed_user_id = mcr_proc_data.user_id
    # db start id at 1, code at 0
    true_class_id = mcr_proc_data.prediction_id + 1

    # Scrapped because of the limitation of the microprocessor
    # image_data = base64.b64decode(data.image)
    # img = io.BytesIO(image_data)
    # _, _, _, _, _, cloud_name, cloud_api, cloud_secret, _ = load_config()
    # image_uri = upload_image_to_cloudinary(cloud_name, cloud_api, cloud_secret, img)
    image_uri = f"image_{uuid.uuid4().hex}.jpg"

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get class_name from class table
        cur.execute("SELECT class_name FROM class WHERE class_id = %s", (true_class_id,))
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Invalid prediction_id: class not found")
        class_name = result[0]

        # Insert into past_prediction
        cur.execute("""
            INSERT INTO past_prediction (user_id, image_uri, prediction, class_name, insertion_timestamp)
            VALUES (%s, %s, %s, %s, NOW())
        """, (fixed_user_id, image_uri, true_class_id, class_name))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Prediction logged successfully", "image_uri": image_uri}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/register")
async def register_handler(payload: RegisterRequest):
    try:
        register_user(
            user_name=payload.user_name,
            email=payload.email,
            password=payload.password,
            user_role=payload.user_role
        )
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


scheduler = BackgroundScheduler()

# Schedule it to run every 2 minutes
trigger = IntervalTrigger(minutes=2)
scheduler.add_job(demo_email_sender_task, trigger)
scheduler.start()
