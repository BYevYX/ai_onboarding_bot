"""
User management service.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.database.models import User, OnboardingSession, UserRole
from app.core.logging import get_logger
from app.core.exceptions import UserNotFoundError, UserAlreadyExistsError

logger = get_logger("services.user")


class UserService:
    """Service for user management operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        position: Optional[str] = None,
        department: Optional[str] = None,
        start_date: Optional[datetime] = None,
        language: str = "ru",
        role: UserRole = UserRole.EMPLOYEE
    ) -> User:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_telegram_id(telegram_id)
            if existing_user:
                raise UserAlreadyExistsError(f"telegram_id:{telegram_id}")
            
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                position=position,
                department=department,
                start_date=start_date,
                language=language,
                role=role,
                last_activity=datetime.utcnow()
            )
            
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            
            logger.info(
                "User created",
                user_id=user.id,
                telegram_id=telegram_id,
                username=username
            )
            
            return user
            
        except UserAlreadyExistsError:
            raise
        except Exception as e:
            logger.error("Failed to create user", error=str(e), telegram_id=telegram_id)
            raise
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user by ID", error=str(e), user_id=user_id)
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user by Telegram ID", error=str(e), telegram_id=telegram_id)
            return None
    
    async def get_user_with_onboarding(self, user_id: int) -> Optional[User]:
        """Get user with onboarding sessions."""
        try:
            stmt = (
                select(User)
                .options(selectinload(User.onboarding_sessions))
                .where(User.id == user_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error("Failed to get user with onboarding", error=str(e), user_id=user_id)
            return None
    
    async def update_user(
        self,
        user_id: int,
        **updates
    ) -> Optional[User]:
        """Update user information."""
        try:
            # Add updated_at timestamp
            updates['updated_at'] = datetime.utcnow()
            
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**updates)
                .returning(User)
            )
            
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                logger.info("User updated", user_id=user_id, updates=list(updates.keys()))
            else:
                logger.warning("User not found for update", user_id=user_id)
            
            return user
            
        except Exception as e:
            logger.error("Failed to update user", error=str(e), user_id=user_id)
            return None
    
    async def update_last_activity(self, user_id: int) -> bool:
        """Update user's last activity timestamp."""
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(last_activity=datetime.utcnow())
            )
            
            await self.db.execute(stmt)
            return True
            
        except Exception as e:
            logger.error("Failed to update last activity", error=str(e), user_id=user_id)
            return False
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user (soft delete)."""
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(is_active=False, updated_at=datetime.utcnow())
            )
            
            result = await self.db.execute(stmt)
            success = result.rowcount > 0
            
            if success:
                logger.info("User deactivated", user_id=user_id)
            else:
                logger.warning("User not found for deactivation", user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error("Failed to deactivate user", error=str(e), user_id=user_id)
            return False
    
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        department: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[UserRole] = None
    ) -> List[User]:
        """List users with filtering and pagination."""
        try:
            stmt = select(User)
            
            # Apply filters
            if department:
                stmt = stmt.where(User.department == department)
            if is_active is not None:
                stmt = stmt.where(User.is_active == is_active)
            if role:
                stmt = stmt.where(User.role == role)
            
            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)
            stmt = stmt.order_by(User.created_at.desc())
            
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            logger.info(
                "Users listed",
                count=len(users),
                skip=skip,
                limit=limit,
                department=department,
                is_active=is_active
            )
            
            return list(users)
            
        except Exception as e:
            logger.error("Failed to list users", error=str(e))
            return []
    
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            # Total users
            total_stmt = select(User.id).where(User.is_active == True)
            total_result = await self.db.execute(total_stmt)
            total_users = len(total_result.scalars().all())
            
            # Users by department
            dept_stmt = select(User.department, User.id).where(User.is_active == True)
            dept_result = await self.db.execute(dept_stmt)
            dept_data = dept_result.all()
            
            departments = {}
            for dept, user_id in dept_data:
                dept_name = dept or "Unknown"
                departments[dept_name] = departments.get(dept_name, 0) + 1
            
            # Users by role
            role_stmt = select(User.role, User.id).where(User.is_active == True)
            role_result = await self.db.execute(role_stmt)
            role_data = role_result.all()
            
            roles = {}
            for role, user_id in role_data:
                role_name = role.value if role else "Unknown"
                roles[role_name] = roles.get(role_name, 0) + 1
            
            stats = {
                "total_users": total_users,
                "departments": departments,
                "roles": roles,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info("User stats generated", total_users=total_users)
            return stats
            
        except Exception as e:
            logger.error("Failed to get user stats", error=str(e))
            return {
                "total_users": 0,
                "departments": {},
                "roles": {},
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def search_users(
        self,
        query: str,
        limit: int = 50
    ) -> List[User]:
        """Search users by name, username, or email."""
        try:
            search_pattern = f"%{query.lower()}%"
            
            stmt = (
                select(User)
                .where(
                    (User.first_name.ilike(search_pattern)) |
                    (User.last_name.ilike(search_pattern)) |
                    (User.username.ilike(search_pattern)) |
                    (User.email.ilike(search_pattern))
                )
                .where(User.is_active == True)
                .limit(limit)
                .order_by(User.first_name, User.last_name)
            )
            
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            logger.info("User search completed", query=query, results=len(users))
            return list(users)
            
        except Exception as e:
            logger.error("Failed to search users", error=str(e), query=query)
            return []