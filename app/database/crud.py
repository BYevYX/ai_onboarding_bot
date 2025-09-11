"""
CRUD operations for database models.
"""

from typing import Optional, List, Dict, Any, Type, TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload

from app.database.models import (
    User, Document, UserDocument, ChatMessage, Notification,
    UserPreferences, DocumentVersion, DocumentType, 
    DocumentStatus, FileProcessingStatus
)

ModelType = TypeVar("ModelType")


class BaseCRUD(Generic[ModelType]):
    """Base CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """Get multiple records with pagination and filters."""
        query = select(self.model)
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update an existing record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def delete(self, db: AsyncSession, id: int) -> bool:
        """Delete a record by ID."""
        result = await db.execute(delete(self.model).where(self.model.id == id))
        await db.commit()
        return result.rowcount > 0
    
    async def count(self, db: AsyncSession, **filters) -> int:
        """Count records with filters."""
        query = select(func.count(self.model.id))
        
        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar()


class UserCRUD(BaseCRUD[User]):
    """CRUD operations for User model."""
    
    async def get_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_with_preferences(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user with preferences."""
        result = await db.execute(
            select(User)
            .options(selectinload(User.preferences))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(self, db: AsyncSession) -> List[User]:
        """Get all active users."""
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()
    
    async def update_last_activity(self, db: AsyncSession, user_id: int) -> bool:
        """Update user's last activity timestamp."""
        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_activity=func.now())
        )
        await db.commit()
        return result.rowcount > 0


class DocumentCRUD(BaseCRUD[Document]):
    """CRUD operations for Document model."""
    
    async def get_by_document_id(self, db: AsyncSession, document_id: str) -> Optional[Document]:
        """Get document by document_id (vector store ID)."""
        result = await db.execute(
            select(Document).where(Document.document_id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def get_published_documents(
        self, 
        db: AsyncSession, 
        department: Optional[str] = None,
        document_type: Optional[DocumentType] = None
    ) -> List[Document]:
        """Get published documents with optional filters."""
        query = select(Document).where(
            and_(
                Document.status == DocumentStatus.PUBLISHED,
                Document.is_active == True
            )
        )
        
        if department:
            query = query.where(Document.department == department)
        
        if document_type:
            query = query.where(Document.document_type == document_type)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_documents_for_processing(self, db: AsyncSession) -> List[Document]:
        """Get documents that need processing."""
        result = await db.execute(
            select(Document).where(
                Document.processing_status == FileProcessingStatus.PENDING
            )
        )
        return result.scalars().all()
    
    async def update_processing_status(
        self, 
        db: AsyncSession, 
        document_id: int, 
        status: FileProcessingStatus,
        error: Optional[str] = None
    ) -> bool:
        """Update document processing status."""
        values = {"processing_status": status}
        if error:
            values["processing_error"] = error
        if status == FileProcessingStatus.COMPLETED:
            values["indexed_at"] = func.now()
            values["is_indexed"] = True
        
        result = await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**values)
        )
        await db.commit()
        return result.rowcount > 0


class UserDocumentCRUD(BaseCRUD[UserDocument]):
    """CRUD operations for UserDocument model."""
    
    async def get_user_document(
        self, 
        db: AsyncSession, 
        user_id: int, 
        document_id: int
    ) -> Optional[UserDocument]:
        """Get user-document relationship."""
        result = await db.execute(
            select(UserDocument).where(
                and_(
                    UserDocument.user_id == user_id,
                    UserDocument.document_id == document_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_documents(
        self, 
        db: AsyncSession, 
        user_id: int,
        completed: Optional[bool] = None
    ) -> List[UserDocument]:
        """Get user's documents with optional completion filter."""
        query = select(UserDocument).where(UserDocument.user_id == user_id)
        
        if completed is not None:
            query = query.where(UserDocument.is_completed == completed)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def mark_document_completed(
        self, 
        db: AsyncSession, 
        user_id: int, 
        document_id: int,
        completion_score: Optional[float] = None
    ) -> bool:
        """Mark document as completed for user."""
        values = {
            "is_completed": True,
            "completed_at": func.now()
        }
        if completion_score is not None:
            values["completion_score"] = completion_score
        
        result = await db.execute(
            update(UserDocument)
            .where(
                and_(
                    UserDocument.user_id == user_id,
                    UserDocument.document_id == document_id
                )
            )
            .values(**values)
        )
        await db.commit()
        return result.rowcount > 0


class NotificationCRUD(BaseCRUD[Notification]):
    """CRUD operations for Notification model."""
    
    async def get_user_notifications(
        self, 
        db: AsyncSession, 
        user_id: int,
        unread_only: bool = False
    ) -> List[Notification]:
        """Get user's notifications."""
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        query = query.order_by(Notification.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    
    async def mark_as_read(self, db: AsyncSession, notification_id: int) -> bool:
        """Mark notification as read."""
        result = await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(is_read=True, read_at=func.now())
        )
        await db.commit()
        return result.rowcount > 0
    
    async def get_pending_notifications(self, db: AsyncSession) -> List[Notification]:
        """Get notifications that need to be sent."""
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.is_sent == False,
                    or_(
                        Notification.scheduled_at.is_(None),
                        Notification.scheduled_at <= func.now()
                    )
                )
            )
        )
        return result.scalars().all()


# CRUD instances
user_crud = UserCRUD(User)
document_crud = DocumentCRUD(Document)
user_document_crud = UserDocumentCRUD(UserDocument)
notification_crud = NotificationCRUD(Notification)

# Base CRUD instances for other models
chat_message_crud = BaseCRUD(ChatMessage)
user_preferences_crud = BaseCRUD(UserPreferences)
document_version_crud = BaseCRUD(DocumentVersion)
