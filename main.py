# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routes.system_constant_routes import router as system_constant_routes
from app.config.constant import ALLOWED_ORIGINS, APP_NAME
from app.routes import (
    user_routes,
    permission_routes,    
    template_routes,
    project_routes,
    user_sorting_routes,
    ws_routes,
)
from app.routes.ms_routes import router as ms_router
from app.database import Base, engine, get_db_session
from app.models.system_constant import SystemConstant
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.routes.label_routes import router as label_router
from app.routes.project_task_routes import router as project_task_routes
from app.routes.template_task_routes import router as template_task_routes
from app.routes.project_task_mapping_routes import router as project_task_mapping_routes
 
 
app = FastAPI(
    title=APP_NAME,
    description="Teams Project Management Backend API",
    version="1.0.0",
)
 
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Create tables
Base.metadata.create_all(bind=engine)
 
 
def seed_system_constants_if_empty(db: Session):
    if db.query(SystemConstant).count() > 0:
        return
    script_path = os.path.join(os.path.dirname(__file__), "sql_script", "schema.sql")
    if not os.path.exists(script_path):
        print("schema.sql not found")
        return
    with open(script_path, "r", encoding="utf-8") as f:
        sql = f.read()
    statements = [s.strip() for s in sql.split(";") if s.strip() and "INSERT INTO system_constants" in s.upper()]
    for stmt in statements:
        db.execute(text(stmt))
    db.commit()
    print("System constants seeded!")
 
with get_db_session() as db:
    seed_system_constants_if_empty(db)
 
 
app.include_router(user_routes, prefix="/api/users", tags=["Users"])
app.include_router(permission_routes, prefix="/api/permissions", tags=["Permissions"])
app.include_router(template_routes, prefix="/api/templates", tags=["Templates & Tasks"])
app.include_router(template_task_routes, prefix="/api/templates", tags=["Templates & Tasks"])
app.include_router(project_routes, prefix="/api/projects", tags=["Projects & Tasks"])
app.include_router(project_task_routes, prefix="/api/projects", tags=["Projects & Tasks"])
app.include_router(system_constant_routes)
app.include_router(label_router, prefix="/api/labels", tags=["Labels"])
app.include_router(project_task_mapping_routes, prefix="/api/labels", tags=["Labels"])
app.include_router(user_sorting_routes, prefix="/api/user-sorting", tags=["User Sorting"]   )
app.include_router(ms_router, prefix="/api/microsoft")
 
 

app.include_router(ws_routes, prefix="/api")


@app.get("/")
def root():
    return {"message": "Teams Project Management API - LIVE!"}