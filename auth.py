"""
JWT-based authentication module.
Roles: guest (restricted filter), user (full access), admin (can edit categories)
"""

import jwt
import hashlib
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Simple SHA256 hash for password comparison."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(username: str, role: str, filter_expr: str | None, secret: str, expire_hours: int) -> str:
    """Create a JWT token."""
    payload = {
        "sub": username,
        "role": role,
        "filter": filter_expr,
        "exp": datetime.utcnow() + timedelta(hours=expire_hours),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class AuthManager:
    """Manages authentication state and token validation."""
    
    def __init__(self, config: dict):
        auth_config = config.get("auth", {})
        self.secret = auth_config.get("jwtSecret", "default_secret_change_me")
        self.expire_hours = auth_config.get("tokenExpireHours", 24)
        self.users = auth_config.get("users", {})
        self.guest_config = auth_config.get("guest", {"enabled": False, "filter": None})
    
    def authenticate(self, username: str, password: str) -> dict | None:
        """Authenticate user and return token info if valid."""
        user = self.users.get(username)
        if not user:
            return None
        
        # Direct password comparison (passwords in config are plaintext for simplicity)
        if user["password"] != password:
            return None
        
        token = create_token(
            username=username,
            role=user["role"],
            filter_expr=user.get("filter"),
            secret=self.secret,
            expire_hours=self.expire_hours
        )
        
        return {
            "token": token,
            "username": username,
            "role": user["role"],
            "filter": user.get("filter"),
            "expiresIn": self.expire_hours * 3600
        }
    
    def create_guest_token(self) -> dict | None:
        """Create a guest token without password."""
        if not self.guest_config.get("enabled", False):
            return None
        
        token = create_token(
            username="guest",
            role="guest",
            filter_expr=self.guest_config.get("filter"),
            secret=self.secret,
            expire_hours=self.expire_hours
        )
        
        return {
            "token": token,
            "username": "guest",
            "role": "guest",
            "filter": self.guest_config.get("filter"),
            "expiresIn": self.expire_hours * 3600
        }
    
    def validate_token(self, token: str) -> dict | None:
        """Validate token and return payload."""
        return decode_token(token, self.secret)
    
    def get_user_from_request(self, request: Request) -> dict | None:
        """Extract and validate user from request (cookie or header)."""
        # Try cookie first
        token = request.cookies.get("auth_token")
        
        # Then try Authorization header
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if not token:
            return None
        
        return self.validate_token(token)


def require_auth(auth_manager: AuthManager):
    """Dependency that requires authentication."""
    async def dependency(request: Request):
        user = auth_manager.get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user
    return dependency


def require_role(auth_manager: AuthManager, allowed_roles: list[str]):
    """Dependency that requires specific role(s)."""
    async def dependency(request: Request):
        user = auth_manager.get_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
