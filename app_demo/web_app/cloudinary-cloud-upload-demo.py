import os
import uuid

import cloudinary
import cloudinary.api
import cloudinary.uploader
from dotenv import load_dotenv
import streamlit as st


# Load database credentials
def load_cloud_config(dotenv_path="web_app/.env"):
    load_dotenv(dotenv_path=dotenv_path)
    CLOUD_NAME = os.getenv("CLOUD_NAME")
    CLOUD_KEY = os.getenv("CLOUD_KEY")
    CLOUD_SECRET = os.getenv("CLOUD_SECRET")
    return CLOUD_NAME, CLOUD_KEY, CLOUD_SECRET


def upload_image_to_cloudinary(cloud_name, api_key, api_secret, image_bytes, extension="png"):
    unique_name = f"predictions/{uuid.uuid4()}.{extension}"
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

def main():
    cloud_name, cloud_key, cloud_secret = load_cloud_config()
    img = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    if img:
        st.text("Your uploaded image:")
        st.image(img, use_container_width=True)
        image_uri = upload_image_to_cloudinary(cloud_name, cloud_key, cloud_secret, img)

if __name__ == "__main__":
    main()
