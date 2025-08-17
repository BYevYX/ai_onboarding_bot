"""
SQLAlchemy database models for the onboarding system.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, JSON, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.connection import Base


class UserRole(PyEnum):
    """User roles enumeration."""
    ADMIN = "admin"
    HR = "hr"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class OnboardingStage(PyEnum):
    """Onboarding stages enumeration."""
    NOT_STARTED = "not_started"
    WELCOME = "welcome"
    PROFILE_SETUP = "profile_setup"
    DOCUMENT_REVIEW = "document_review"
    QUESTIONS_ANSWERS = "questions_answers"
    COMPLETED = "completed"


class DocumentType(PyEnum):
    """Document types enumeration."""
    HANDBOOK = "handbook"
    POLICY = "policy"
    PROCEDURE = "procedure"
    FORM = "form"
    GUIDE = "guide"
    OTHER = "other"


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
    language: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    onboarding_sessions: Mapped[List["OnboardingSession"]] = relationship(
        "OnboardingSession", back_populates="user", cascade="all, delete-orphan"
    )
    user_documents: Mapped[List["UserDocument"]] = relationship(
        "UserDocument", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class OnboardingSession(Base):
    """Onboarding session model."""
    
    __tablename__ = "onboarding_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Session state
    stage: Mapped[OnboardingStage] = mapped_column(
        Enum(OnboardingStage), 
        default=OnboardingStage.NOT_STARTED, 
        index=True
    )
    completion_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Progress tracking
    documents_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    questions_asked: Mapped[int] = mapped_column(Integer, default=0)
    
    # Session data
    session_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Store workflow state
    context: Mapped[Optional[str]] = mapped_column(Text)  # Current context
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_interaction: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="onboarding_sessions")
    
    def __repr__(self) -> str:
        return f"<OnboardingSession(id={self.id}, user_id={self.user_id}, stage='{self.stage}')>"


class Document(Base):
    """Document model."""
    
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Vector store ID
    
    # Document metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Classification
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    language: Mapped[str] = mapped_column(String(10), default="ru", index=True)
    
    # Content
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256 hash
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Relationships
    user_documents: Mapped[List["UserDocument"]] = relationship(
        "UserDocument", back_populates="document", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', type='{self.document_type}')>"


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
    onboarding_stage: Mapped[Optional[str]] = mapped_column(String(50), index=True)
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


class SystemMetrics(Base):
    """System metrics model for monitoring and analytics."""
    
    __tablename__ = "system_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Metric data
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Dimensions
    dimensions: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional metric dimensions
    
    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_name_timestamp', 'metric_name', 'timestamp'),
    )
    
    def __repr__(self) -> str:
        return f"<SystemMetrics(metric_name='{self.metric_name}', value={self.metric_value})>"


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