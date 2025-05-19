import grpc
from concurrent import futures
from datetime import datetime
from typing import List, Optional
from .auth_pb2 import ( # Corrected import
    UserResponse,
    ListUsersResponse,
    RoleResponse,
    ListRolesResponse,
    UserActivityResponse,
    ActivityEntry,
    DeleteUserResponse,
    AssignRoleResponse,
    RevokeRoleResponse
)
from .auth_pb2_grpc import ( # Corrected import
    UserManagementServiceServicer,
    add_UserManagementServiceServicer_to_server
)
from .models import User, Role, ActivityLog # Corrected import
from .user_manager import UserManager # Corrected import

class UserService(UserManagementServiceServicer):
    def __init__(self, redis_client, user_manager: Optional[UserManager] = None) -> None:
        self.user_manager = user_manager if user_manager else UserManager(redis_client)

    def CreateUser(self, request, context):
        try:
            user = self.user_manager.create_user(
                username=request.username,
                email=request.email,
                password=request.password,
                initial_roles=request.initial_roles
            )
            return self._user_to_response(user)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserResponse()

    def GetUser(self, request, context):
        user = self.user_manager.get_user(request.user_id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("User not found")
            return UserResponse()
        return self._user_to_response(user)

    def UpdateUser(self, request, context):
        try:
            user = self.user_manager.update_user(
                user_id=request.user_id,
                username=request.username,
                email=request.email,
                password=request.password,
                is_active=request.is_active
            )
            return self._user_to_response(user)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return UserResponse()

    def DeleteUser(self, request, context):
        success = self.user_manager.delete_user(request.user_id)
        return DeleteUserResponse(success=success)

    def ListUsers(self, request, context):
        users, total = self.user_manager.list_users(
            page=request.page,
            page_size=request.page_size
        )
        return ListUsersResponse(
            users=[self._user_to_response(u) for u in users],
            total_count=total
        )

    def SearchUsers(self, request, context):
        users, total = self.user_manager.search_users(
            query=request.query,
            page=request.page,
            page_size=request.page_size
        )
        return ListUsersResponse(
            users=[self._user_to_response(u) for u in users],
            total_count=total
        )

    def CreateRole(self, request, context):
        role = self.user_manager.create_role(
            name=request.name,
            permissions=request.permissions
        )
        return self._role_to_response(role)

    def AssignRole(self, request, context):
        success = self.user_manager.assign_role(
            user_id=request.user_id,
            role_name=request.role_name
        )
        return AssignRoleResponse(success=success)

    def RevokeRole(self, request, context):
        success = self.user_manager.revoke_role(
            user_id=request.user_id,
            role_name=request.role_name
        )
        return RevokeRoleResponse(success=success)

    def ListRoles(self, request, context):
        roles = self.user_manager.list_roles()
        return ListRolesResponse(roles=[self._role_to_response(r) for r in roles])

    def GetUserActivity(self, request, context):
        activities, total = self.user_manager.get_user_activity(
            user_id=request.user_id,
            start_date=request.start_date,
            end_date=request.end_date,
            page=request.page,
            page_size=request.page_size
        )
        return UserActivityResponse(
            activities=[self._activity_to_entry(a) for a in activities],
            total_count=total
        )

    def _user_to_response(self, user: User) -> UserResponse:
        return UserResponse(
            user_id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
            roles=[r.name for r in user.roles]
        )

    def _role_to_response(self, role: Role) -> RoleResponse:
        return RoleResponse(
            name=role.name,
            permissions=role.permissions,
            created_at=role.created_at.isoformat()
        )

    def _activity_to_entry(self, activity: ActivityLog) -> ActivityEntry:
        return ActivityEntry(
            action=activity.action,
            timestamp=activity.timestamp.isoformat(),
            ip_address=activity.ip_address,
            user_agent=activity.user_agent,
            metadata=activity.metadata
        )