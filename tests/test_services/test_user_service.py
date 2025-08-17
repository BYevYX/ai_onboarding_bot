"""
Tests for user service.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from app.services.user_service import UserService
from app.database.models import User, UserRole
from app.core.exceptions import UserAlreadyExistsError


class TestUserService:
    """Test user service operations."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_db_session, sample_user_data):
        """Test user creation."""
        service = UserService(test_db_session)
        
        user = await service.create_user(**sample_user_data)
        
        assert user.id is not None
        assert user.telegram_id == sample_user_data["telegram_id"]
        assert user.username == sample_user_data["username"]
        assert user.first_name == sample_user_data["first_name"]
        assert user.last_name == sample_user_data["last_name"]
        assert user.email == sample_user_data["email"]
        assert user.position == sample_user_data["position"]
        assert user.department == sample_user_data["department"]
        assert user.language == sample_user_data["language"]
        assert user.role == UserRole.EMPLOYEE
        assert user.is_active == True
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, test_db_session, sample_user_data):
        """Test creating duplicate user raises exception."""
        service = UserService(test_db_session)
        
        # Create first user
        await service.create_user(**sample_user_data)
        
        # Try to create duplicate
        with pytest.raises(UserAlreadyExistsError):
            await service.create_user(**sample_user_data)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, test_db_session, sample_user_data):
        """Test getting user by ID."""
        service = UserService(test_db_session)
        
        # Create user
        created_user = await service.create_user(**sample_user_data)
        
        # Get user by ID
        retrieved_user = await service.get_user_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.telegram_id == sample_user_data["telegram_id"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id(self, test_db_session, sample_user_data):
        """Test getting user by Telegram ID."""
        service = UserService(test_db_session)
        
        # Create user
        await service.create_user(**sample_user_data)
        
        # Get user by Telegram ID
        retrieved_user = await service.get_user_by_telegram_id(sample_user_data["telegram_id"])
        
        assert retrieved_user is not None
        assert retrieved_user.telegram_id == sample_user_data["telegram_id"]
        assert retrieved_user.username == sample_user_data["username"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, test_db_session):
        """Test getting non-existent user returns None."""
        service = UserService(test_db_session)
        
        user = await service.get_user_by_id(999)
        assert user is None
        
        user = await service.get_user_by_telegram_id(999999999)
        assert user is None
    
    @pytest.mark.asyncio
    async def test_update_user(self, test_db_session, sample_user_data):
        """Test updating user information."""
        service = UserService(test_db_session)
        
        # Create user
        created_user = await service.create_user(**sample_user_data)
        
        # Update user
        updates = {
            "first_name": "Updated",
            "position": "Senior Developer",
            "language": "en"
        }
        
        updated_user = await service.update_user(created_user.id, **updates)
        
        assert updated_user is not None
        assert updated_user.first_name == "Updated"
        assert updated_user.position == "Senior Developer"
        assert updated_user.language == "en"
        assert updated_user.last_name == sample_user_data["last_name"]  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_last_activity(self, test_db_session, sample_user_data):
        """Test updating user's last activity."""
        service = UserService(test_db_session)
        
        # Create user
        created_user = await service.create_user(**sample_user_data)
        original_activity = created_user.last_activity
        
        # Update last activity
        success = await service.update_last_activity(created_user.id)
        
        assert success == True
        
        # Verify activity was updated
        updated_user = await service.get_user_by_id(created_user.id)
        assert updated_user.last_activity > original_activity
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, test_db_session, sample_user_data):
        """Test deactivating user."""
        service = UserService(test_db_session)
        
        # Create user
        created_user = await service.create_user(**sample_user_data)
        assert created_user.is_active == True
        
        # Deactivate user
        success = await service.deactivate_user(created_user.id)
        
        assert success == True
        
        # Verify user is deactivated
        updated_user = await service.get_user_by_id(created_user.id)
        assert updated_user.is_active == False
    
    @pytest.mark.asyncio
    async def test_list_users(self, test_db_session):
        """Test listing users with pagination and filtering."""
        service = UserService(test_db_session)
        
        # Create multiple users
        users_data = [
            {"telegram_id": 111, "username": "user1", "department": "IT", "first_name": "User1"},
            {"telegram_id": 222, "username": "user2", "department": "HR", "first_name": "User2"},
            {"telegram_id": 333, "username": "user3", "department": "IT", "first_name": "User3"},
        ]
        
        for user_data in users_data:
            await service.create_user(**user_data)
        
        # Test listing all users
        all_users = await service.list_users()
        assert len(all_users) == 3
        
        # Test filtering by department
        it_users = await service.list_users(department="IT")
        assert len(it_users) == 2
        
        # Test pagination
        first_page = await service.list_users(skip=0, limit=2)
        assert len(first_page) == 2
        
        second_page = await service.list_users(skip=2, limit=2)
        assert len(second_page) == 1
    
    @pytest.mark.asyncio
    async def test_search_users(self, test_db_session):
        """Test searching users."""
        service = UserService(test_db_session)
        
        # Create users with different names
        users_data = [
            {"telegram_id": 111, "username": "john_doe", "first_name": "John", "last_name": "Doe"},
            {"telegram_id": 222, "username": "jane_smith", "first_name": "Jane", "last_name": "Smith"},
            {"telegram_id": 333, "username": "bob_johnson", "first_name": "Bob", "last_name": "Johnson"},
        ]
        
        for user_data in users_data:
            await service.create_user(**user_data)
        
        # Search by first name
        john_users = await service.search_users("John")
        assert len(john_users) == 1
        assert john_users[0].first_name == "John"
        
        # Search by username
        jane_users = await service.search_users("jane_smith")
        assert len(jane_users) == 1
        assert jane_users[0].username == "jane_smith"
        
        # Search by partial match
        j_users = await service.search_users("j")
        assert len(j_users) >= 2  # John and Jane
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self, test_db_session):
        """Test getting user statistics."""
        service = UserService(test_db_session)
        
        # Create users in different departments
        users_data = [
            {"telegram_id": 111, "department": "IT", "role": UserRole.EMPLOYEE},
            {"telegram_id": 222, "department": "IT", "role": UserRole.MANAGER},
            {"telegram_id": 333, "department": "HR", "role": UserRole.HR},
            {"telegram_id": 444, "department": "HR", "role": UserRole.EMPLOYEE},
        ]
        
        for user_data in users_data:
            await service.create_user(**user_data)
        
        stats = await service.get_user_stats()
        
        assert stats["total_users"] == 4
        assert stats["departments"]["IT"] == 2
        assert stats["departments"]["HR"] == 2
        assert stats["roles"]["employee"] == 2
        assert stats["roles"]["manager"] == 1
        assert stats["roles"]["hr"] == 1
        assert "generated_at" in stats