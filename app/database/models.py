"""
SQLAlchemy database models for the onboarding system.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from app.database.connection import Base


class UserRole(PyEnum):
    """User roles enumeration."""
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class DocumentType(PyEnum):
    """Document types enumeration."""
    HANDBOOK = "handbook"
    POLICY = "policy"
    PROCEDURE = "procedure"
    FORM = "form"
    GUIDE = "guide"
    TRAINING = "training"
    PRESENTATION = "presentation"
    VIDEO = "video"
    QUIZ = "quiz"
    OTHER = "other"


class DocumentStatus(PyEnum):
    """Document status enumeration."""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class NotificationType(PyEnum):
    """Notification types enumeration."""
    WELCOME = "welcome"
    DOCUMENT_ASSIGNED = "document_assigned"
    DOCUMENT_REMINDER = "document_reminder"
    QUIZ_AVAILABLE = "quiz_available"
    ONBOARDING_COMPLETE = "onboarding_complete"
    SYSTEM = "system"


class FileProcessingStatus(PyEnum):
    """File processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Work information
    position: Mapped[Optional[str]] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # System fields
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.EMPLOYEE, index=True)
    language: Mapped[str] = mapped_column(String(2), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user_documents: Mapped[List["UserDocument"]] = relationship(
        "UserDocument", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class Document(Base):
    """Document model."""
    
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Vector store ID
    uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    
    # Document metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Classification
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), index=True)
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.DRAFT, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    language: Mapped[str] = mapped_column(String(10), default="ru", index=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Content processing
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256 hash
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    processing_status: Mapped[FileProcessingStatus] = mapped_column(
        Enum(FileProcessingStatus),
        default=FileProcessingStatus.PENDING,
        index=True
    )
    processing_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documents.id"))
    
    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    required_roles: Mapped[Optional[List[str]]] = mapped_column(JSON)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user_documents: Mapped[List["UserDocument"]] = relationship(
        "UserDocument", back_populates="document", cascade="all, delete-orphan"
    )
    child_documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="parent_document", remote_side=[id]
    )
    parent_document: Mapped[Optional["Document"]] = relationship(
        "Document", back_populates="child_documents", remote_side=[parent_document_id]
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}', status='{self.status}')>"


class UserDocument(Base):
    """User-Document relationship model for tracking document interactions."""
    
    __tablename__ = "user_documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Interaction tracking
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Progress
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    completion_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_documents")
    document: Mapped["Document"] = relationship("Document", back_populates="user_documents")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'document_id', name='uq_user_document'),
        Index('idx_user_document_completion', 'user_id', 'is_completed'),
    )
    
    def __repr__(self) -> str:
        return f"<UserDocument(user_id={self.user_id}, document_id={self.document_id}, completed={self.is_completed})>"


class ChatMessage(Base):
    """Chat message model for storing conversation history."""
    
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Message metadata
    message_type: Mapped[str] = mapped_column(String(50), default="user", index=True)  # user, system, ai
    language: Mapped[str] = mapped_column(String(10), default="ru")
    
    # Context
    context_used: Mapped[Optional[str]] = mapped_column(Text)  # RAG context
    
    # Processing metadata
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_messages")
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, user_id={self.user_id}, type='{self.message_type}')>"


class AuditLog(Base):
    """Audit log model for tracking system events."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Event information
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Actor information
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    actor_type: Mapped[str] = mapped_column(String(50), default="user", index=True)  # user, system, admin
    
    # Event data
    event_data: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_event_user', 'event_type', 'user_id'),
        Index('idx_audit_created', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', user_id={self.user_id})>"


class Notification(Base):
    """Notification model for user notifications."""
    
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), index=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index('idx_notification_user_read', 'user_id', 'is_read'),
        Index('idx_notification_scheduled', 'scheduled_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}')>"


class UserPreferences(Base):
    """User preferences model."""
    
    __tablename__ = "user_preferences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    telegram_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_frequency_hours: Mapped[int] = mapped_column(Integer, default=24)
    
    # Interface preferences
    theme: Mapped[str] = mapped_column(String(20), default="light")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Learning preferences
    preferred_content_types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    difficulty_level: Mapped[str] = mapped_column(String(20), default="intermediate")
    
    # Custom settings
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, user_id={self.user_id})>"


class DocumentVersion(Base):
    """Document version tracking model."""
    
    __tablename__ = "document_versions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False)
    
    # Version info
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_name: Mapped[Optional[str]] = mapped_column(String(100))
    change_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # File info
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Metadata
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships
    document: Mapped["Document"] = relationship("Document")
    creator: Mapped[Optional["User"]] = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('document_id', 'version_number', name='uq_document_version'),
        Index('idx_document_version_current', 'document_id', 'is_current'),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentVersion(id={self.id}, document_id={self.document_id}, version={self.version_number})>"