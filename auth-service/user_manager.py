from datetime import datetime
from typing import List, Optional, Dict
from models import User, Role, ActivityLog

class UserManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        # Initialize in-memory storage (replace with DB in production)
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.activity_logs: List[ActivityLog] = []

    # User operations
    def create_user(self, username: str, email: str, password: str, initial_roles: List[str] = []) -> User:
        user_id = f"user_{len(self.users) + 1}"
        user = User(
            id=user_id,
            username=username,
            email=email,
            password=password,  # Note: Should be hashed in production
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            roles=[self.get_role(r) for r in initial_roles if self.get_role(r)]
        )
        self.users[user_id] = user
        self._log_activity(user_id, "USER_CREATED")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def update_user(self, user_id: str, username: Optional[str] = None, 
                   email: Optional[str] = None, password: Optional[str] = None,
                   is_active: Optional[bool] = None) -> User:
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")

        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if password is not None:
            user.password = password  # Note: Should be hashed in production
        if is_active is not None:
            user.is_active = is_active

        user.updated_at = datetime.now()
        self._log_activity(user_id, "USER_UPDATED")
        return user

    def delete_user(self, user_id: str) -> bool:
        if user_id in self.users:
            del self.users[user_id]
            self._log_activity(user_id, "USER_DELETED")
            return True
        return False

    def list_users(self, page: int = 1, page_size: int = 10) -> tuple[List[User], int]:
        users = list(self.users.values())
        start = (page - 1) * page_size
        end = start + page_size
        return users[start:end], len(users)

    def search_users(self, query: str, page: int = 1, page_size: int = 10) -> tuple[List[User], int]:
        results = [
            u for u in self.users.values()
            if query.lower() in u.username.lower() or query.lower() in u.email.lower()
        ]
        start = (page - 1) * page_size
        end = start + page_size
        return results[start:end], len(results)

    # Role operations
    def create_role(self, name: str, permissions: List[str]) -> Role:
        role = Role(
            name=name,
            permissions=permissions,
            created_at=datetime.now()
        )
        self.roles[name] = role
        return role

    def get_role(self, name: str) -> Optional[Role]:
        return self.roles.get(name)

    def assign_role(self, user_id: str, role_name: str) -> bool:
        user = self.users.get(user_id)
        role = self.roles.get(role_name)
        if not user or not role:
            return False

        if role not in user.roles:
            user.roles.append(role)
            user.updated_at = datetime.now()
            self._log_activity(user_id, "ROLE_ASSIGNED", {"role": role_name})
            return True
        return False

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        user = self.users.get(user_id)
        role = self.roles.get(role_name)
        if not user or not role:
            return False

        if role in user.roles:
            user.roles.remove(role)
            user.updated_at = datetime.now()
            self._log_activity(user_id, "ROLE_REVOKED", {"role": role_name})
            return True
        return False

    def list_roles(self) -> List[Role]:
        return list(self.roles.values())

    # Activity logging
    def get_user_activity(self, user_id: str, start_date: Optional[str] = None,
                         end_date: Optional[str] = None, page: int = 1,
                         page_size: int = 10) -> tuple[List[ActivityLog], int]:
        logs = [log for log in self.activity_logs if log.user_id == user_id]
        
        if start_date:
            start = datetime.fromisoformat(start_date)
            logs = [log for log in logs if log.timestamp >= start]
        if end_date:
            end = datetime.fromisoformat(end_date)
            logs = [log for log in logs if log.timestamp <= end]

        logs.sort(key=lambda x: x.timestamp, reverse=True)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return logs[start_idx:end_idx], len(logs)

    def _log_activity(self, user_id: str, action: str, metadata: Optional[Dict] = None):
        log = ActivityLog(
            user_id=user_id,
            action=action,
            timestamp=datetime.now(),
            ip_address="127.0.0.1",  # Would be real IP in production
            user_agent="system",      # Would be real user agent in production
            metadata=metadata or {}
        )
        self.activity_logs.append(log)