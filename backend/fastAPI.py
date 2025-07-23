from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Union
import torch
from torchvision import transforms
from PIL import Image
import io
import numpy as np
import psycopg2
from psycopg2.extras import DictCursor
import os
from datetime import datetime
from torchvision import models
import torch.nn as nn
import torch.nn.functional as F
from config import DB_CONFIG
from fastapi.staticfiles import StaticFiles

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
model_path = "models/mobilenet_transfer_v1_model.pth"
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve images from the ./images directory at the /images URL path
app.mount("/images", StaticFiles(directory="images"), name="images")

class MistakeReport(BaseModel):
    image_id: int
    corrected_class: Union[int, str]

class PredictionResponse(BaseModel):
    predicted_class: str
    confidence: float
    image_id: int
    prediction_source: str
    timestamp: Optional[datetime] = None
    corrected_class: Optional[str] = None
    image_url: Optional[str] = None

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

CLASSES = ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"]

@app.post("/predict", response_model=PredictionResponse)
async def predict_image(file: UploadFile = File(...), prediction_source: str = "WebApp", user_id: int = None):
    try:
        # Read and preprocess image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image = transform(image)
        image = image.unsqueeze(0)

        # Make prediction
        with torch.no_grad():
            outputs = model(image)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted_class_idx = torch.max(probabilities, 1)
            predicted_class_idx = predicted_class_idx.item()
            confidence = confidence.item()
            predicted_class = CLASSES[predicted_class_idx]

        # Save uploaded image with image_id
        images_dir = "./images"
        os.makedirs(images_dir, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ".jpg"

        # Store in database, let image_id auto-increment, and save extension
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO predictions (predicted_class, confidence, prediction_source, prediction_type, timestamp, user_id, image_extension)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING image_id, timestamp
                    """,
                    (predicted_class, confidence, prediction_source, "Single", datetime.utcnow(), user_id, None)
                )
                row = cursor.fetchone()
                conn.commit()
                image_id, timestamp = row[0], row[1]

        image_filename = f"image_{image_id}{ext}"
        image_path = os.path.join(images_dir, image_filename)
        with open(image_path, "wb") as f:
            f.write(image_data)
        image_url = f"/images/{image_filename}"
        # Update the image_extension column to store the filename
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE predictions SET image_extension = %s WHERE image_id = %s
                    """,
                    (image_filename, image_id)
                )
                conn.commit()
        return {
            "predicted_class": predicted_class,
            "confidence": confidence,
            "image_id": image_id,
            "prediction_source": prediction_source,
            "timestamp": timestamp,
            "image_url": image_url,
            "user_id": user_id,
            "image_extension": image_filename
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Model file error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/report-mistake")
async def report_mistake(report: MistakeReport):
    try:
        # Convert index to class name if needed
        corrected_class_value = report.corrected_class
        if isinstance(corrected_class_value, int):
            if 0 <= corrected_class_value < len(CLASSES):
                corrected_class_value = CLASSES[corrected_class_value]
            else:
                corrected_class_value = None
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE predictions
                    SET corrected_class = %s
                    WHERE image_id = %s
                    RETURNING image_id
                    """,
                    (corrected_class_value, report.image_id)
                )
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Prediction not found")
                conn.commit()
        return {"message": "Correction saved", "image_id": report.image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving correction: {str(e)}")

@app.get("/predictions", response_model=List[PredictionResponse])
async def past_predictions(start_date: str, end_date: str, prediction_source: str = "All", user_id: int = None):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

                query = """
                    SELECT image_id, predicted_class, confidence, prediction_source, timestamp, corrected_class, user_id, image_extension
                    FROM predictions
                    WHERE timestamp::DATE BETWEEN %s AND %s
                """
                params = [start_date, end_date]
                if prediction_source.lower() != "all":
                    query += " AND LOWER(prediction_source) = LOWER(%s)"
                    params.append(prediction_source)
                if user_id is not None:
                    query += " AND user_id = %s"
                    params.append(user_id)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    image_filename = row["image_extension"] if row["image_extension"] else f"image_{row['image_id']}.jpg"
                    image_url = f"/images/{image_filename}"
                    results.append({
                        "image_id": row["image_id"],
                        "predicted_class": row["predicted_class"],
                        "confidence": row["confidence"],
                        "prediction_source": row["prediction_source"],
                        "timestamp": row["timestamp"],
                        "corrected_class": row["corrected_class"],
                        "user_id": row["user_id"],
                        "image_url": image_url,
                        "image_extension": image_filename
                    })
                return results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@app.get("/users")
async def get_users():
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute('SELECT user_id, user_name, email FROM "user" ORDER BY user_name')
                users = cursor.fetchall()
                return [
                    {
                        "user_id": row["user_id"],
                        "user_name": row["user_name"],
                        "email": row["email"]
                    }
                    for row in users
                ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")