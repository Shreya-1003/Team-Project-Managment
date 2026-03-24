import os
from datetime import datetime, timedelta
from typing import Optional
from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from dotenv import load_dotenv

from app.models.user import User

load_dotenv()

AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

# Create Blob Service Client
blob_service_client = BlobServiceClient(
    account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=AZURE_STORAGE_ACCOUNT_KEY
)

container_client = blob_service_client.get_container_client(
    AZURE_CONTAINER_NAME
)


from azure.storage.blob import ContentSettings

def upload_bytes_to_blob(blob_name: str, content: bytes, content_type: str):
    """
    Upload image bytes directly to Azure Blob
    """
    print(
        "Uploading blob:", blob_name,
        "Content type:", content_type,
        "Size:", len(content)
    )

    blob_client = container_client.get_blob_client(blob_name)

    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(
            content_type=content_type
        )
    )

    return blob_client.url



def delete_blob(blob_name: str):
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.delete_blob()


def generate_blob_sas_url(blob_name: str, expiry_minutes: int = 60) -> str:
    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name=AZURE_CONTAINER_NAME,
        blob_name=blob_name,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
    )
    print("Generated SAS token:", sas_token)    
    return (
        f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/"
        f"{AZURE_CONTAINER_NAME}/{blob_name}?"
        f"{sas_token}"
    )




BLOB_BASE_URL = os.getenv("BLOB_BASE_URL")  

def get_profile_picture_url(user: User, use_sas: bool = True, expiry_minutes: int = 60) -> Optional[str]:

    if not user.profile_picture:
        return None
    
    if use_sas:
        return generate_blob_sas_url(user.profile_picture, expiry_minutes)
    else:
        BLOB_BASE_URL = os.getenv("BLOB_BASE_URL")
        return f"{BLOB_BASE_URL}/{user.profile_picture}"
