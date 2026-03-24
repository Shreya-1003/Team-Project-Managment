# from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# from fastapi.security.utils import get_authorization_scheme_param
# from app.helpers.auth import _decode_jwt_payload
# from app.websockets.manager import manager

# router = APIRouter()

# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     try:
#         # ✅ Accept first (important)
#         await websocket.accept()

#         # ✅ Read Authorization header manually
#         auth_header = websocket.headers.get("authorization")

#         if not auth_header:
#             await websocket.close(code=1008)
#             return

#         scheme, token = get_authorization_scheme_param(auth_header)

#         if scheme.lower() != "bearer" or not token:
#             await websocket.close(code=1008)
#             return

#         # ✅ Reuse SAME decoder from auth.py
#         claims = _decode_jwt_payload(token)

#         user_id = (
#             claims.get("preferred_username")
#             or claims.get("upn")

#         )

#         if not user_id:
#             await websocket.close(code=1008)
#             return

#         print(
#             f"WS connected: user_id={user_id}, "
#             f" oid={claims.get('oid')}"
#         )

#         await manager.connect(user_id, websocket)

#         while True:
#             await websocket.receive_text()

#     except WebSocketDisconnect:
#         manager.disconnect(user_id, websocket)
#         print(f"WS disconnected: {user_id}")

#     except Exception as e:
#         print(f"WS auth error: {e}")
#         await websocket.close(code=1008)



from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.helpers.auth import _decode_jwt_payload
from app.websockets.manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user_id = None

    try:
        # ✅ 1. Accept connection
        await websocket.accept()

        # ✅ 2. Read token from query params
        token = websocket.query_params.get("token")

        if not token:
            print("WS rejected: token missing")
            await websocket.close(code=1008)
            return

        # ✅ 3. Decode JWT (reuse auth.py logic)
        claims = _decode_jwt_payload(token)

        user_id = (
            claims.get("preferred_username")
            or claims.get("upn")
            or claims.get("email")
        )

        if not user_id:
            print("WS rejected: user_id not found in token")
            await websocket.close(code=1008)
            return

        print(
            f"WS connected: user_id={user_id}, "
            f"oid={claims.get('oid')}"
        )

        # ✅ 4. Register connection
        await manager.connect(user_id, websocket)

        # ✅ 5. Keep connection alive
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id, websocket)
        print(f"WS disconnected: {user_id}")

    except Exception as e:
        print(f"WS auth error: {e}")
        await websocket.close(code=1008)
