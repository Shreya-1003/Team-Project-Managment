from datetime import datetime,time,timedelta,date
import os
from typing import List
from zoneinfo import ZoneInfo
from fastapi import HTTPException, Response
from sqlalchemy.orm import Session
from app.models.label import Label
from app.models.project import Project
from app.models.system_constant import SystemConstant
from app.models.user import User
from app.models.user_permission_mapping import UserPermissionMapping
from app.schemas.label_schema import SimpleLabelOut
from app.models.project_task_mapping import ProjectTaskMapping
from app.models.template_task_mapping import TemplateTaskMapping
from app.models.labels_project_task_mapping import LabelsProjectTaskMapping
from app.config.constant import DEPENDENCY_TYPE
from typing import Iterable, Dict, Optional
from datetime import datetime, date, timedelta
from typing import Optional, Union
from dotenv import load_dotenv
import requests
from fastapi.responses import StreamingResponse
from io import BytesIO
from app.helpers.azure_blob import upload_bytes_to_blob
import uuid

 

DateLike = Union[datetime, date]
 
 
def to_date(dt: Optional[DateLike]) -> Optional[date]:
    if dt is None:
        return None
    if hasattr(dt, 'date'):
        return dt.date()
    return dt  
 
 
def _as_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)
 
def _load_project_labels(db: Session, project_id: int):
    rows = (
        db.query(LabelsProjectTaskMapping, Label)
        .join(Label, LabelsProjectTaskMapping.label_id == Label.labels_id)
        .filter(
            LabelsProjectTaskMapping.project_id == project_id,
            LabelsProjectTaskMapping.is_active == True,
            Label.is_active == True,
        )
        .order_by(Label.sort_order, Label.labels_id)  
        .all()
    )
 
    project_labels: List[SimpleLabelOut] = []
    task_labels: Dict[int, List[SimpleLabelOut]] = {}
 
    for mapping, label in rows:
        if mapping.task_id is None:
            dto = SimpleLabelOut(
                labels_project_task_mapping_id=mapping.labels_project_task_mapping_id,
                label_id=label.labels_id,
                label_text=label.label_text,
                project_label_category_id=mapping.project_label_category_id,
                sort_order=label.sort_order,        
            )
            project_labels.append(dto)
        else:
            dto = SimpleLabelOut(
                labels_project_task_mapping_id=mapping.labels_project_task_mapping_id,
                label_id=label.labels_id,
                label_text=label.label_text,
                project_label_category_id=None,
                sort_order=label.sort_order,          
            )
            task_labels.setdefault(mapping.task_id, []).append(dto)
 
    return project_labels, task_labels
 
 
 
def _get_dependency_type_ids(db: Session) -> dict[str, int]:
    parent = (
        db.query(SystemConstant)
        .filter(
            SystemConstant.id == DEPENDENCY_TYPE,      
            SystemConstant.is_active == True,
        )
        .first()
    )
    if not parent:
        return {}
    rows = (
        db.query(SystemConstant)
        .filter(
            SystemConstant.type == parent.type,        
            SystemConstant.is_active == True,
        )
        .all()
    )
    result: dict[str, int] = {}
    for r in rows:
        result[r.name] = r.id
    return result
 
 
def clone_template_tasks_to_project(
    db: Session,
    template_id: int,
    project_id: int,
    created_by: str,
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.is_active == True)
        .first()
    )
    if not project:
        return
 
    base_date = project.start_date
    if base_date is not None and hasattr(base_date, "date"):
        base_date = base_date.date()
 
    templates = (
        db.query(TemplateTaskMapping)
        .filter(
            TemplateTaskMapping.template_id == template_id,
            TemplateTaskMapping.is_active == True,
        )
        .order_by(
            TemplateTaskMapping.parent_id,
            TemplateTaskMapping.sort_order,
            TemplateTaskMapping.template_task_mapping_id,
        )
        .all()
    )
    if not templates:
        return
 
    dep_ids = _get_dependency_type_ids(db)
    before_id = dep_ids.get("Before")
    after_id = dep_ids.get("After")
 
    id_map: dict[int, int] = {}
 
    for tt in templates:
        if base_date is not None:
            default_start = base_date
        else:
            default_start = None
 
        start_date = default_start
        if base_date is not None and tt.dependent_taskid is None:
            start_date = base_date
 
        pt = ProjectTaskMapping(
            project_id=project_id,
            task_name=tt.task_name,
            priority_id=tt.priority_id,
            is_milestone=tt.isMilestone,
            dependency_type=tt.dependency_type,
            days_offset=tt.days_offset or 0,
            parent_id=None,          
            dependent_task_id=None,  
            start_date=start_date,
            end_date=None,
            status_id=tt.status_id,
            created_by=created_by,
            is_active=True,
            sort_order=tt.sort_order,
        )
        db.add(pt)
        db.flush()
        id_map[tt.template_task_mapping_id] = pt.id
 
    db.flush()
 
    for tt in templates:
        new_id = id_map[tt.template_task_mapping_id]
        pt = (
            db.query(ProjectTaskMapping)
            .filter(ProjectTaskMapping.id == new_id)
            .first()
        )
 
        if tt.parent_id:
            pt.parent_id = id_map.get(tt.parent_id)
 
        if tt.dependent_taskid and base_date is not None:
            dep_pt_id = id_map.get(tt.dependent_taskid)
            if dep_pt_id:
                dep_pt = (
                    db.query(ProjectTaskMapping)
                    .filter(ProjectTaskMapping.id == dep_pt_id)
                    .first()
                )
                if dep_pt and dep_pt.start_date:
                    dep_date = dep_pt.start_date
                    if hasattr(dep_date, "date"):
                        dep_date = dep_date.date()
 
                    offset = tt.days_offset or 0
 
                    if tt.dependency_type == after_id:
                        # AFTER: start after N days from dependent task
                        pt.start_date = dep_date + timedelta(days=offset)
                    elif tt.dependency_type == before_id:
                        # BEFORE: start N days before dependent task
                        pt.start_date = dep_date - timedelta(days=offset)
                    else:
                        # unknown dependency_type: fallback to project start + offset
                        if base_date is not None:
                            pt.start_date = base_date + timedelta(days=offset)
 
                    pt.dependent_task_id = dep_pt_id
        else:
            # no dependency: ensure start date = project start date
            if base_date is not None:
                pt.start_date = base_date
 
    db.commit()
    project_tasks = (
        db.query(ProjectTaskMapping)
        .filter(
            ProjectTaskMapping.project_id == project_id,
            ProjectTaskMapping.is_active == True,
            ProjectTaskMapping.id.in_(id_map.values()),
        )
        .all()
    )
    recompute_schedule_for_tasks(db, base_date, project_tasks)
 
 
def _add_workdays(base: date | datetime | None, offset: int) -> date | None:
    if base is None:
        return None
 
    if hasattr(base, "date"):
        base = base.date()
 
    current = base
 
    if offset == 0:
        while current.weekday() >= 5:  
            current += timedelta(days=1)
        return current
 
    step = 1 if offset > 0 else -1
    remaining = abs(offset)
    while remaining > 0:
        current += timedelta(days=step)
        if current.weekday() < 5:  
            remaining -= 1
 
    while current.weekday() >= 5:
        current += timedelta(days=1)
 
    return current
 
 


def recompute_schedule_for_tasks(db: Session, base_date, tasks: Iterable[ProjectTaskMapping], preserve_ids: Optional[set] = None) -> None:


    if not base_date:
        return
    if hasattr(base_date, "date"):
        base_date = base_date.date()
    
    tasks_list = list(tasks)
    if not tasks_list:
        return
    
    # ✅ FIXED: Build COMPLETE dependency graph
    by_id = {t.id: t for t in tasks_list}
    dependents = {t.id: [] for t in tasks_list}  # Who depends on me?
    
    for t in tasks_list:
        if t.dependent_task_id and t.dependent_task_id in by_id:
            dependents[t.dependent_task_id].append(t.id)
    
    dep_ids = _get_dependency_type_ids(db)
    after_id = dep_ids.get("After")
    before_id = dep_ids.get("Before")
    
    # Memoization & cycle-detection sets
    computed: set[int] = set()
    visiting: set[int] = set()

    def compute_task_date(task_id: int):
        """Recursively compute date for task and ALL dependents with cycle detection"""
        if task_id not in by_id:
            return

        if task_id in computed:
            return

        if task_id in visiting:
            # Cycle detected; avoid infinite recursion
            print(f"⚠️ CYCLE detected at task {task_id}; skipping to avoid recursion")
            return

        visiting.add(task_id)
        task = by_id[task_id]

        previous_end = to_date(task.end_date)

        # If task already has an explicit end_date, decide whether to keep it based on preserve_ids
        if task.end_date is not None:
            keep = False
            if preserve_ids is None:
                # default behavior: keep any explicit date (keeps create behavior unchanged)
                keep = True
            elif task.id in preserve_ids:
                keep = True

            if keep:
                # Ensure start_date mirrors end_date (milestone)
                if task.start_date is None:
                    task.start_date = task.end_date
                print(f"TASK {task.id} kept (explicit date): {task.end_date}")

                visiting.remove(task_id)
                computed.add(task_id)

                # Still cascade to dependents using this date
                for dep_task_id in dependents.get(task_id, []):
                    compute_task_date(dep_task_id)
                return

        # BASE CASE: No dependency -> project start
        if not task.dependent_task_id:
            new_end = base_date
        else:
            dep_id = task.dependent_task_id
            # Guard: self-dependency or missing dependency -> treat as no-dependency
            if dep_id == task_id or dep_id not in by_id:
                new_end = base_date
            else:
                # Ensure dependency computed first
                compute_task_date(dep_id)
                dep_task = by_id.get(dep_id)
                if dep_task and dep_task.end_date:
                    dep_date = dep_task.end_date
                    if hasattr(dep_date, "date"):
                        dep_date = dep_date.date()
                    offset = task.days_offset or 0
                    if task.dependency_type == after_id:
                        new_end = _add_workdays(dep_date, offset)
                    elif task.dependency_type == before_id:
                        new_end = _add_workdays(dep_date, -offset)
                    else:
                        new_end = _add_workdays(base_date, offset)
                else:
                    new_end = base_date

        # Apply computed dates
        task.end_date = new_end
        task.start_date = new_end
        print(f"TASK {task.id} updated: {previous_end} -> {task.end_date}")

        visiting.remove(task_id)
        computed.add(task_id)

        # CASCADE: Update ALL dependents
        for dep_task_id in dependents.get(task_id, []):
            compute_task_date(dep_task_id)

    # Start from ALL root tasks (no incoming dependencies)
    roots = [t.id for t in tasks_list if not t.dependent_task_id]
    for root_id in roots:
        compute_task_date(root_id)

    # Ensure any remaining tasks (e.g., cycles or isolated groups) are processed
    for t_id in by_id.keys():
        if t_id not in computed:
            compute_task_date(t_id)

    db.commit()
    print("✅ RECOMPUTE COMPLETE - All dependencies resolved")


 
 
def _get_user_ids(db: Session, permission_id: int) -> List[int]:
    rows = (
        db.query(UserPermissionMapping.user_id)
        .filter(
            UserPermissionMapping.permission_id == permission_id,
            UserPermissionMapping.is_active == True,
        )
        .all()
    )
    return [r[0] for r in rows]
 
 
def get_project_due_bucket(
    start_dt: Optional[DateLike],
    end_dt: Optional[DateLike],
):
    ist_tz = ZoneInfo("Asia/Kolkata")
    today = datetime.now(ist_tz).date()
 
    end_date = to_date(end_dt)
    start_date = to_date(start_dt)
 
    if end_date is not None:
        due = end_date
    elif start_date is not None:
        due = start_date
    else:
        return "no_date"
 
    if due < today:
        return "late"
    if due == today:
        return "today"
    if due == today + timedelta(days=1):
        return "tomorrow"
 
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)
    if start_week <= due <= end_week:
        return "this_week"
 
    start_next = start_week + timedelta(days=7)
    end_next = start_next + timedelta(days=6)
    if start_next <= due <= end_next:
        return "next_week"
 
    if due > end_next:
        return "future"
 
    return "no_date"
 
 

 
 
load_dotenv()
 
TENANT_ID = os.getenv("TENANT_ID" )
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
 
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
 
def get_graph_access_token():
    """Get Microsoft Graph access token"""
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        raise HTTPException(status_code=500, detail="Microsoft credentials missing in .env")
   
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
   
    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Token failed: {response.text}")
    print("🔹 Graph token obtained",response)
    return response.json()["access_token"]
 
def get_microsoft_user(user_id: str):
    """Get user by ID/Email"""
    token = get_graph_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
   
    response = requests.get(f"{GRAPH_BASE_URL}/users", headers=headers)
    if response.status_code != 200:
        error_detail = response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
        raise HTTPException(status_code=response.status_code, detail=error_detail)
   
    return response.json()
 
 
def validate_user(check_username: str) -> dict:
    try:
        graph_user = get_microsoft_user(check_username)
        graph_email = graph_user.get('mail', '').lower()
        graph_upn = graph_user.get('userPrincipalName', '').lower()
       
        if check_username.lower() not in [graph_email, graph_upn]:
            return {  
                "valid": False,
                "reason": f"User '{check_username}' not found in Microsoft Graph"
            }
    except Exception:
        return {
            "valid": False,
            "reason": "User not found in Microsoft Graph"
        }
   
    return {
        "valid": True,
        "username": check_username
    }




def get_microsoft_user_photo_proxy(user_id: str):
    token = get_graph_access_token()
    # print("GRAPH TOKEN:", token)

    url = f"{GRAPH_BASE_URL}/users/{user_id}/photo/$value"

    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "image/*"
        },
        timeout=10
    )

    print("GRAPH STATUS:", response.status_code)
    print("CONTENT LENGTH:", len(response.content))

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="User has no profile photo")

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail="Failed to fetch photo from Microsoft Graph"
        )

    return Response(
        content=response.content,
        media_type=response.headers.get("Content-Type", "image/jpeg"),
        headers={
            "Cache-Control": "public, max-age=86400"
        }
    )




# def upload_user_photo_to_blob(user_id: str):
#     token = get_graph_access_token()

#     response = requests.get(
#         f"{GRAPH_BASE_URL}/users/{user_id}/photo/$value",
#         headers={"Authorization": f"Bearer {token}"},
#     )

#     if response.status_code == 404:
#         raise HTTPException(status_code=404, detail="User has no photo")

#     if response.status_code != 200:
#         raise HTTPException(status_code=500, detail=response.text)
    
#     print(f"🔹 Photo fetched for user {user_id}, size={len(response.content)} bytes")

#     # 🔹 Blob name
#     blob_name = f"user-photos/{user_id}_{uuid.uuid4()}.jpg"

#     blob_url = upload_bytes_to_blob(
#         blob_name=blob_name,
#         content=response.content,
#         content_type=response.headers.get("Content-Type", "image/jpeg")
#     )

#     return {
#         "blob_url": blob_url,
#         "blob_name": blob_name
#     }



def upload_user_photo_to_blob(user_id: str, db: Session, user: User):  # Keep user_id
    token = get_graph_access_token()

    response = requests.get(
        f"{GRAPH_BASE_URL}/users/{user_id}/photo/$value",  # ✅ user_id for Graph API
        headers={"Authorization": f"Bearer {token}"},
    )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="User has no photo")

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=response.text)
    
    print(f"🔹 Photo fetched for user {user_id}, size={len(response.content)} bytes")

    # 🔹 Blob name using USERNAME from DB (not user_id)
    blob_name = f"user-photos/{user.username}_{uuid.uuid4()}.jpg"  # ✅ user.username

    blob_url = upload_bytes_to_blob(
        blob_name=blob_name,
        content=response.content,
        content_type=response.headers.get("Content-Type", "image/jpeg")
    )

    # 🔹 Save to DB
    user.profile_picture = blob_name
    db.commit()
    db.refresh(user)

    return {
        "blob_url": blob_url,
        "blob_name": blob_name,
        "profile_picture": True
    }
