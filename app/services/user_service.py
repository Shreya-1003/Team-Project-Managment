from fastapi import APIRouter, HTTPException, Query, status, Depends
from sqlalchemy.orm import Session
from app.helpers.auth import get_current_user
from app.helpers.azure_blob import get_profile_picture_url
from app.schemas.user_schema import UserPermissionUpdateResult
from app.database import get_db
from app.models.permission import Permission
from app.models.user import User
from app.models.user_permission_mapping import UserPermissionMapping
from app.models.user_task_mapping import UserTaskMapping
from app.models.project_task_mapping import ProjectTaskMapping
from app.models.system_constant import SystemConstant
from app.helpers.utils import validate_user 
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserTaskCreate,
    UserTaskUpdate,
    UserTaskResponse,
    UserPermissionCreate,
    UserPermissionUpdate,
    UserPermissionResponse,
)
from app.config.constant import USER_STATUS
from app.schemas.authschema import CurrentUser


router = APIRouter(tags=["Users"])


    # @staticmethod
    # def create_user(payload: UserCreate, db: Session ,current_user: CurrentUser):
    #     existing = (
    #         db.query(User)
    #         .filter(
    #             User.username == payload.username,   
    #             User.is_active == True,
    #         )
    #         .first()
    #     )
    #     if existing:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="User with this username already exists",
    #         )
    #     status_id = payload.status_id
    #     if status_id is None:
    #         row = db.query(SystemConstant).filter(
    #             SystemConstant.id == USER_STATUS,
    #             SystemConstant.is_active == True,
    #         ).first()
    #         if row:
    #             status_id = row.id

    #     data = payload.model_dump()
    #     data["status_id"] = status_id
    #     data["created_by"] = current_user.username

    #     user = User(**data)
    #     db.add(user)
    #     db.commit()
    #     db.refresh(user)
    #     return user

class UserService:
    @staticmethod
    def create_user(payload: UserCreate, db: Session, current_user: CurrentUser):

        username = payload.username.lower().strip()
        print(f"🔍 Our Token OK: {current_user.username}")

        # Check if user exists 
        deleted_user = db.query(User).filter(
            User.username == username,
            User.is_active == False
        ).first()

        # Run Graph validation ONLY if user was never in DB
        if not deleted_user:
            graph_result = validate_user(username)
            if not graph_result.get("valid", False):
                raise HTTPException(
                    status_code=404,
                    detail=f"User '{username}' not found"
                )
            print(f"✅ Graph API OK: {username}")
        else:
            print(f"♻️ Soft-deleted user found, skipping Graph validation: {username}")

        #   Block ONLY if active user exists
        active_user = db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()

        if active_user:
            print(f"ℹ️ Active user already exists: {username}")
            return active_user

        #  Create NEW user row
        status_id = payload.status_id
        if status_id is None:
            row = db.query(SystemConstant).filter(
                SystemConstant.id == USER_STATUS,
                SystemConstant.is_active == True
            ).first()
            if row:
                status_id = row.id

        data = payload.model_dump()
        data["username"] = username
        data["status_id"] = status_id
        data["created_by"] = current_user.username
        data["is_active"] = True

        user = User(**data)
        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"🆕 NEW User CREATED: {username}")
        return user



    @staticmethod
    def get_all_users(db: Session = Depends(get_db)):
        users = db.query(User).filter(User.is_active == True).all()
        if not users:
            return []

        user_ids = [u.user_id for u in users]

        mappings = (
            db.query(
                UserPermissionMapping,
                Permission.permission_type,
                Permission.permission_bracket,
            )
            .join(Permission, UserPermissionMapping.permission_id == Permission.id)
            .filter(
                UserPermissionMapping.user_id.in_(user_ids),
                UserPermissionMapping.is_active == True,
                Permission.is_active == True,
            )
            .all()
        )

        mapping_by_user: dict[int, list[tuple]] = {}
        for m, p_type, p_bracket in mappings:
            mapping_by_user.setdefault(m.user_id, []).append((m, p_type, p_bracket))

        result: list[UserResponse] = []
        for u in users:
            rows = mapping_by_user.get(u.user_id, [])
            permission_mapping_ids = [m.id for m, _, _ in rows]
            permission_ids = [m.permission_id for m, _, _ in rows]
            permission_types = [ptype for _, ptype, _ in rows]
            permission_brackets = [pbr for _, _, pbr in rows]

            result.append(
                UserResponse(
                    user_id=u.user_id,
                    username=u.username,
                    status_id=u.status_id,
                    created_by=u.created_by,
                    modified_by=u.modified_by,
                    created_at=u.created_at,
                    modified_at=u.modified_at,
                    is_active=u.is_active,
                    permission_mapping_ids=permission_mapping_ids,
                    permission_ids=permission_ids,
                    permission_types=permission_types,
                    permission_brackets=permission_brackets,
                    profile_picture=u.profile_picture,
                    profile_picture_url=get_profile_picture_url(u)
                )
            )

        return result


    @staticmethod
    def get_user(
        db: Session,
        current_user: CurrentUser,
    ):
        user_id = current_user.user_id

        user = (
            db.query(User)
            .filter(User.user_id == user_id, User.is_active == True)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        rows = (
            db.query(
                UserPermissionMapping,
                Permission.permission_type,
                Permission.permission_bracket,
            )
            .join(Permission, UserPermissionMapping.permission_id == Permission.id)
            .filter(
                UserPermissionMapping.user_id == user_id,
                UserPermissionMapping.is_active == True,
                Permission.is_active == True,
            )
            .all()
        )

        permission_mapping_ids = [m.id for m, _, _ in rows]
        permission_ids = [m.permission_id for m, _, _ in rows]
        permission_types = [ptype for _, ptype, _ in rows]
        permission_brackets = [pbr for _, _, pbr in rows]

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            status_id=user.status_id,
            created_by=user.created_by,
            modified_by=user.modified_by,
            created_at=user.created_at,
            modified_at=user.modified_at,
            is_active=user.is_active,
            permission_mapping_ids=permission_mapping_ids,
            permission_ids=permission_ids,
            permission_types=permission_types,
            permission_brackets=permission_brackets,
            profile_picture=user.profile_picture,
            profile_picture_url=get_profile_picture_url(user)
        )

    @staticmethod
    def update_user(user_id: int, payload: UserUpdate,db: Session,
    current_user: CurrentUser,):
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(404, "User not found")

        data = payload.model_dump(exclude_unset=True)

        # if "username" in data and data["username"]:
        #     data["modified_by"] = data["username"]

        if "status_id" in data and data["status_id"] is not None:
            status_row = db.query(SystemConstant).filter(
                SystemConstant.id == data["status_id"],
                SystemConstant.is_active == True,
            ).first()
            if not status_row:
                raise HTTPException(400, "Invalid status_id")

        for k, v in data.items():
            setattr(user, k, v)
        user.modified_by = current_user.username
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(user_id: int, db: Session = Depends(get_db)):
        # 1️⃣ Fetch only ACTIVE user
        user = (
            db.query(User)
            .filter(User.user_id == user_id, User.is_active == True)
            .first()
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2️⃣  delete user-task mappings 
        db.query(UserTaskMapping).filter(
            UserTaskMapping.user_id == user_id
        ).update(
            {UserTaskMapping.is_active: False},
            synchronize_session=False,
        )

        # 3️⃣ Soft delete user
        db.query(User).filter(
            User.user_id == user_id
        ).update(
            {User.is_active: False},
            synchronize_session=False,
        )

        db.commit()

        return {"message": "User soft deleted successfully"}

    # ---------- ASSIGN USER TO TASK  ----------
    
    @staticmethod
    def assign_user_to_task(
        user_id: int,
        task_id: int,
        payload: UserTaskCreate,
        db: Session ,
        current_user: CurrentUser,
    ):
        user = (
            db.query(User)
            .filter(User.user_id == user_id, User.is_active == True)
            .first()
        )
        if not user:
            raise HTTPException(404, "User not found")

        task = (
            db.query(ProjectTaskMapping)
            .filter(
                ProjectTaskMapping.id == task_id,
                ProjectTaskMapping.is_active == True,
            )
            .first()
        )
        if not task:
            raise HTTPException(404, "Task not found")

        created_by = current_user.username
        # if payload.created_by_user_id:
        #     creator = (
        #         db.query(User)
        #         .filter(
        #             User.user_id == payload.created_by_user_id,
        #             User.is_active == True,
        #         )
        #         .first()
        #     )
        #     if not creator:
        #         raise HTTPException(404, "Creator user not found")
        #     created_by = creator.username
        # else:
        #     created_by = user.username

        mapping = (
            db.query(UserTaskMapping)
            .filter(
                UserTaskMapping.user_id == user_id,
                UserTaskMapping.task_id == task_id,
            )
            .first()
        )
        if mapping:
            mapping.is_active = True
            mapping.modified_by = current_user.username
        else:
            mapping = UserTaskMapping(
                user_id=user_id,
                task_id=task_id,
                is_active=True,
                created_by=current_user.username,
            )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping
            
    @staticmethod
    def list_user_task_mappings(user_id: int, db: Session = Depends(get_db)):
        mappings = (
            db.query(UserTaskMapping)
            .filter(
                UserTaskMapping.user_id == user_id,
                UserTaskMapping.is_active == True,
                UserTaskMapping.task_id != None
            )
            .all()
        )
        result: list[UserTaskResponse] = []
        for m in mappings:
            result.append(
                UserTaskResponse(
                    id=m.id,
                    user_id=m.user_id,
                    task_id=m.task_id,         
                    created_by=m.created_by,
                    modified_by=m.modified_by,
                    created_at=m.created_at,
                    modified_at=m.modified_at,
                    is_active=m.is_active,
                    profile_picture=m.profile_picture,           # ✅ Fixed: Use user.profile_picture
                    profile_picture_url=get_profile_picture_url(m)           # ✅ Fixed: Use get_profile_picture_url(user        
                )
            )
        return result
    
    @staticmethod
    def update_user_task_mapping(
        mapping_id: int,
        payload: UserTaskUpdate,
        db: Session ,
        current_user: CurrentUser,
    ):
        mapping = db.query(UserTaskMapping).filter(UserTaskMapping.id == mapping_id).first()
        if not mapping or not mapping.is_active:
            raise HTTPException(404, "Mapping not found")

        data = payload.model_dump(exclude_unset=True)

        if "task_id" in data and data["task_id"] is not None:
            task = (
                db.query(ProjectTaskMapping)
                .filter(
                    ProjectTaskMapping.id == data["task_id"],
                    ProjectTaskMapping.is_active == True,
                )
                .first()
            )
            if not task:
                raise HTTPException(400, "Invalid task_id")
        if data.get("modified_by_user_id"):
            modifier = (
                db.query(User)
                .filter(
                    User.user_id == data["modified_by_user_id"],
                    User.is_active == True,
                )
                .first()
            )
            if not modifier:
                raise HTTPException(404, "Modifier user not found")
            data["modified_by"] = modifier.username
            data.pop("modified_by_user_id", None)

        for k, v in data.items():
            setattr(mapping, k, v)
        
        mapping.modified_by = current_user.username

        db.commit()
        db.refresh(mapping)
        return mapping
    
    # @staticmethod
    # def delete_user_task_mapping(mapping_id: int, db: Session = Depends(get_db)):
    #     mapping = (
    #         db.query(UserTaskMapping)
    #         .filter(UserTaskMapping.id == mapping_id)
    #         .first()
    #     )
    #     if not mapping:
    #         raise HTTPException(404, "Mapping not found")

    #     db.delete(mapping)
    #     db.commit()
    #     return None
    
    
    # ---------- USER <-> PERMISSION MAPPING ----------
    
    @staticmethod
    def create_user_permissions(
        payload: UserPermissionCreate,
        db: Session ,
        current_user: CurrentUser,
    ):

        user = (
            db.query(User)
            .filter(User.user_id == payload.user_id, User.is_active == True)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user.user_id

        created_mappings: list[int] = []
        created_permissions: list[int] = []

        for pid in payload.permission_id:
            perm = (
                db.query(Permission)
                .filter(Permission.id == pid, Permission.is_active == True)
                .first()
            )
            if not perm:
                continue

            mapping = UserPermissionMapping(
                user_id=user_id,
                permission_id=pid,
                created_by=current_user.username,
            )
            db.add(mapping)
            db.flush()

            created_mappings.append(mapping.id)
            created_permissions.append(pid)

        db.commit()

        return {
            "user_id": user_id,
            "created_mapping_id": created_mappings,
            "permission_id": created_permissions,
            "profile_picture": user.profile_picture,     
            "profile_picture_url": get_profile_picture_url(user),
        }
        
    @staticmethod
    def update_user_permissions(
        payload: UserPermissionUpdate,
        db: Session,
        current_user: CurrentUser,
    ):
        # ✅ Validate user exists
        user = (
            db.query(User)
            .filter(User.user_id == payload.user_id, User.is_active == True)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        results: list[UserPermissionUpdateResult] = []

        for change in payload.changes:
            mapping = (
                db.query(UserPermissionMapping)
                .filter(
                    UserPermissionMapping.id == change.mapping_id,
                    UserPermissionMapping.user_id == payload.user_id  
                )
                .first()
            )
            if not mapping:
                continue

            if change.is_active is not None:
                mapping.is_active = change.is_active

            if change.permission_id is not None:
                perm = (
                    db.query(Permission)
                    .filter(
                        Permission.id == change.permission_id,
                        Permission.is_active == True,
                    )
                    .first()
                )
                if perm:
                    mapping.permission_id = change.permission_id
            
            mapping.modified_by = current_user.username  
            results.append(
                UserPermissionUpdateResult(
                    user_id=mapping.user_id,
                    permission_ids=[mapping.permission_id],  
                    is_active=mapping.is_active
                )
            )

        db.commit()
        return results


#---------------- Check user exists ---------------------

    @staticmethod
    def user_check(username: str = Query(...), db: Session = Depends(get_db)):    
        user = db.query(User).filter(
            User.username == username.lower(),
            User.is_active == True
        ).first()

        if not user:
            print(f"✅ User NOT found: {username}")
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": f"User '{username}' NOT found in database",
                    "data": {
                        "username": username.lower(), 
                        "exists": False, 
                        "user_id": None
                    }
                }
            )
        
        print(f"❌ User EXISTS: {username} (ID: {user.user_id})")
        return {
            "success": True,
            "message": f"User '{username}' already exists in database",
            "data": {
                "username": user.username, 
                "exists": True, 
                "user_id": user.user_id
            }
        }

    