from fastapi import Header
from app.helpers.utils import get_microsoft_user
 
class MsService:
    @staticmethod
    async def get_user():
        return get_microsoft_user()
 
 
# from fastapi import HTTPException
# from app.helpers.utils import get_microsoft_user
# from app.models.user import User
# from sqlalchemy.orm import Session
# from sqlalchemy import or_
 
# class MsService:
#     @staticmethod
#     def validate_token_and_graph(token_email: str, graph_user_id: str):
 
#         graph_user = get_microsoft_user(graph_user_id)
#         graph_email = graph_user.get('mail', '').lower()
#         graph_upn = graph_user.get('userPrincipalName', '').lower()
       
#         if graph_email != token_email.lower() and graph_upn != token_email.lower():
#             raise HTTPException(
#                 status_code=401,
#                 detail=f"❌ Token email '{token_email}' ≠ Graph email '{graph_email}' | UPN '{graph_upn}'"
#             )
       
#         return {
#             "graph_user": graph_user,
#             "graph_email": graph_email,
#             "graph_upn": graph_upn,
#             "validated": True
#         }
 