"""
Database initialization utilities.
"""

import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database.connection import db_manager, Base
from app.database.models import (
    DocumentType, User, Document, Notification,
    UserRole, DocumentStatus,
    NotificationType, FileProcessingStatus
)
from app.database.crud import (
    user_crud, document_crud, user_preferences_crud, 
    notification_crud
)
from app.core.logging import get_logger

logger = get_logger("database.init")


async def create_tables():
    """Create all database tables."""
    try:
        engine = db_manager.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


async def drop_tables():
    """Drop all database tables."""
    try:
        engine = db_manager.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


async def create_admin_user(db: AsyncSession) -> User:
    """Create default admin user."""
    admin_data = {
        "telegram_id": 123456789,  # Replace with actual admin Telegram ID
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@company.com",
        "role": UserRole.ADMIN,
        "language": "ru",
        "is_active": True,
        "position": "System Administrator",
        "department": "IT"
    }
    
    # Check if admin already exists
    existing_admin = await user_crud.get_by_telegram_id(db, admin_data["telegram_id"])
    if existing_admin:
        logger.info("Admin user already exists")
        return existing_admin
    
    admin_user = await user_crud.create(db, admin_data)
    logger.info(f"Created admin user: {admin_user.username}")
    
    # Create admin preferences
    preferences_data = {
        "user_id": admin_user.id,
        "email_notifications": True,
        "telegram_notifications": True,
        "theme": "dark",
        "timezone": "Europe/Moscow"
    }
    await user_preferences_crud.create(db, preferences_data)
    
    return admin_user


async def create_sample_users(db: AsyncSession) -> List[User]:
    """Create sample users for testing."""
    sample_users_data = [
        {
            "telegram_id": 111111111,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@company.com",
            "role": UserRole.EMPLOYEE,
            "position": "Software Developer",
            "department": "Engineering",
            "language": "en"
        },
        {
            "telegram_id": 222222222,
            "username": "jane_smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@company.com",
            "role": UserRole.HR,
            "position": "HR Manager",
            "department": "Human Resources",
            "language": "ru"
        },
        {
            "telegram_id": 333333333,
            "username": "mike_johnson",
            "first_name": "Mike",
            "last_name": "Johnson",
            "email": "mike.johnson@company.com",
            "role": UserRole.MANAGER,
            "position": "Team Lead",
            "department": "Engineering",
            "language": "en"
        }
    ]
    
    created_users = []
    for user_data in sample_users_data:
        # Check if user already exists
        existing_user = await user_crud.get_by_telegram_id(db, user_data["telegram_id"])
        if existing_user:
            created_users.append(existing_user)
            continue
        
        user = await user_crud.create(db, user_data)
        created_users.append(user)
        
        # Create user preferences
        preferences_data = {
            "user_id": user.id,
            "email_notifications": True,
            "telegram_notifications": True,
            "reminder_frequency_hours": 24,
            "theme": "light",
            "timezone": "UTC"
        }
        await user_preferences_crud.create(db, preferences_data)
        
        logger.info(f"Created sample user: {user.username}")
    
    return created_users


async def create_sample_documents(db: AsyncSession) -> List[Document]:
    """Create sample documents for testing."""
    sample_documents_data = [
        {
            "document_id": "handbook_001",
            "title": "Employee Handbook",
            "description": "Complete guide for new employees",
            "filename": "employee_handbook.pdf",
            "document_type": DocumentType.HANDBOOK,
            "status": DocumentStatus.PUBLISHED,
            "department": "Human Resources",
            "language": "ru",
            "tags": ["onboarding", "policies", "procedures"],
            "is_public": True,
            "processing_status": FileProcessingStatus.COMPLETED,
            "is_indexed": True,
            "chunk_count": 25
        },
        {
            "document_id": "policy_001",
            "title": "Code of Conduct",
            "description": "Company code of conduct and ethics",
            "filename": "code_of_conduct.pdf",
            "document_type": DocumentType.POLICY,
            "status": DocumentStatus.PUBLISHED,
            "department": "Human Resources",
            "language": "ru",
            "tags": ["ethics", "conduct", "policies"],
            "is_public": True,
            "processing_status": FileProcessingStatus.COMPLETED,
            "is_indexed": True,
            "chunk_count": 15
        },
        {
            "document_id": "guide_001",
            "title": "IT Security Guide",
            "description": "Information security guidelines and best practices",
            "filename": "security_guide.pdf",
            "document_type": DocumentType.GUIDE,
            "status": DocumentStatus.PUBLISHED,
            "department": "IT",
            "language": "en",
            "tags": ["security", "IT", "guidelines"],
            "required_roles": ["EMPLOYEE", "MANAGER", "ADMIN"],
            "processing_status": FileProcessingStatus.COMPLETED,
            "is_indexed": True,
            "chunk_count": 20
        },
        {
            "document_id": "training_001",
            "title": "Safety Training Manual",
            "description": "Workplace safety training materials",
            "filename": "safety_training.pdf",
            "document_type": DocumentType.TRAINING,
            "status": DocumentStatus.PUBLISHED,
            "department": "Safety",
            "language": "ru",
            "tags": ["safety", "training", "workplace"],
            "is_public": True,
            "processing_status": FileProcessingStatus.COMPLETED,
            "is_indexed": True,
            "chunk_count": 30
        }
    ]
    
    created_documents = []
    for doc_data in sample_documents_data:
        # Check if document already exists
        existing_doc = await document_crud.get_by_document_id(db, doc_data["document_id"])
        if existing_doc:
            created_documents.append(existing_doc)
            continue
        
        document = await document_crud.create(db, doc_data)
        created_documents.append(document)
        logger.info(f"Created sample document: {document.title}")
    
    return created_documents


async def create_sample_notifications(db: AsyncSession, users: List[User]) -> List[Notification]:
    """Create sample notifications for users."""
    created_notifications = []
    
    for user in users:
        notifications_data = [
            {
                "user_id": user.id,
                "title": "Welcome to the company!",
                "message": "Welcome to our team! Please complete your onboarding process.",
                "notification_type": NotificationType.WELCOME,
                "is_sent": True,
                "sent_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "user_id": user.id,
                "title": "New document assigned",
                "message": "You have been assigned a new document to review: Employee Handbook",
                "notification_type": NotificationType.DOCUMENT_ASSIGNED,
                "is_sent": False,
                "scheduled_at": datetime.utcnow() + timedelta(hours=1)
            }
        ]
        
        for notification_data in notifications_data:
            notification = await notification_crud.create(db, notification_data)
            created_notifications.append(notification)
    
    logger.info(f"Created {len(created_notifications)} sample notifications")
    return created_notifications


async def seed_database():
    """Seed database with initial data."""
    try:
        async for db in db_manager.get_session():
            logger.info("Starting database seeding...")
            
            # Create admin user
            admin_user = await create_admin_user(db)
            
            # Create sample users
            sample_users = await create_sample_users(db)
            all_users = [admin_user] + sample_users
            
            # Create sample documents
            documents = await create_sample_documents(db)
            
            # Create sample notifications
            notifications = await create_sample_notifications(db, sample_users)
            
            logger.info("Database seeding completed successfully")
            logger.info(f"Created: {len(all_users)} users, {len(documents)} documents, "
                       f"{len(notifications)} notifications")
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise


async def init_database(drop_existing: bool = False):
    """Initialize database with tables and seed data."""
    try:
        if drop_existing:
            logger.info("Dropping existing tables...")
            await drop_tables()
        
        logger.info("Creating database tables...")
        await create_tables()
        
        logger.info("Seeding database with initial data...")
        await seed_database()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    # Run database initialization
    asyncio.run(init_database(drop_existing=True))