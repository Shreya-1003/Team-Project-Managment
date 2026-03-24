# app/config/constant.py
import os
from typing import List
 
 
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",   # React default
    "http://localhost:5173",    # Vite default
    "https://localhost:3000",    
    "https://localhost:5173",
    "http://localhost:8000"
   
]
 
APP_NAME = "Teams Project Management API"
APP_VERSION = "1.0.0"
 
 
# Microsoft - All from .env
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# REDIRECT_URI = os.getenv("REDIRECT_URI")
MICROSOFT_SCOPE = os.getenv("MICROSOFT_SCOPE")
   
# Microsoft URLs (built from TENANT_ID)
AUTH_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_URL = "https://graph.microsoft.com/v1.0"
 
 
USER_STATUS_ACTIVE = 1
PROJECT_STATUS_ACTIVE = 6
 
TASK_PRIORITY_LOW = 16
TASK_PRIORITY_MEDIUM = 17
TASK_PRIORITY_HIGH = 18
TASK_PRIORITY_CRITICAL = 19
TASK_STATUS = 11
DEPENDENCY_TYPE =  20
USER_STATUS = 1
LABEL_CATEGORY= 22
LABEL_CATEGORY_DEFAULT = 23
PROJECT_LABEL_CATEGORY = 24
PROJECT_LABEL_CATEGORY_DEFAULT = 25