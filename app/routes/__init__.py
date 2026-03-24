# app/routes/__init__.py

from .user_routes import router as user_routes
from .permission_routes import router as permission_routes
from .template_routes import router as template_routes
from .project_routes import router as project_routes 
from .label_routes import router as label_routes
from .user_sorting_routes import router as user_sorting_routes
# from .user_task_routes import router as user_task_routes
from .ws_routes import router as ws_routes

__all__ = [
    "user_routes",
    "permission_routes",
    "template_routes",
    "project_routes",       
    "label_routes",
    "user_sorting_routes",
    "ws_routes",
]