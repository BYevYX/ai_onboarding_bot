"""
Security utilities including JWT token handling and password hashing.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.security.access_token_expire_minutes
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.security.secret_key, 
        algorithm=settings.security.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token."""
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token, 
            settings.security.secret_key, 
            algorithms=[settings.security.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def generate_telegram_webhook_secret() -> str:
    """Generate a secure webhook secret for Telegram."""
    import secrets
    return secrets.token_urlsafe(32)


class SecurityManager:
    """Security manager for handling authentication and authorization."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def create_user_token(self, user_id: int, telegram_id: int) -> str:
        """Create a token for a user with additional claims."""
        payload = {
            "user_id": user_id,
            "telegram_id": telegram_id,
            "type": "access"
        }
        return create_access_token(subject=payload)
    
    def verify_user_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a user token and return payload."""
        try:
            payload = jwt.decode(
                token,
                self.settings.security.secret_key,
                algorithms=[self.settings.security.algorithm]
            )
            return payload.get("sub")
        except JWTError:
            return None
    
    def check_user_permissions(self, user_role: str, required_permission: str) -> bool:
        """Check if user has required permission based on role."""
        role_permissions = {
            "admin": [
                "read_all", "write_all", "delete_all", 
                "manage_users", "manage_documents", "manage_system"
            ],
            "hr": [
                "read_all", "write_documents", "manage_users", 
                "view_analytics"
            ],
            "manager": [
                "read_team", "write_documents", "view_team_analytics"
            ],
            "employee": [
                "read_own", "write_own"
            ]
        }
        
        return required_permission in role_permissions.get(user_role, [])


# Global security manager instance
security_manager = SecurityManager()