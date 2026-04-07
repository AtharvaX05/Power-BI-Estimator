#!/usr/bin/env python3
"""Test script for password reset functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.auth_service import AuthService
from backend.repositories.memory import InMemoryUserRepository
from backend.models.user import UserCreate
from datetime import datetime, timezone
import uuid

def test_password_reset():
    """Test the password reset functionality."""
    # Setup
    repo = InMemoryUserRepository()
    auth_service = AuthService(repo)

    # Create a test user
    user_data = UserCreate(name="Test User", email="test@example.com", password="oldpassword")
    user = auth_service.register(user_data)
    print(f"✅ Created user: {user.email}")

    # Test initiate password reset
    reset_token = auth_service.initiate_password_reset("test@example.com")
    assert reset_token is not None, "Reset token should be generated"
    print(f"✅ Generated reset token: {reset_token}")

    # Test reset password
    success = auth_service.reset_password(reset_token, "newpassword123")
    assert success, "Password reset should succeed"
    print("✅ Password reset successful")

    # Test login with new password
    login_token = auth_service.login("test@example.com", "newpassword123")
    assert login_token is not None, "Should be able to login with new password"
    print("✅ Login with new password successful")

    # Test login with old password fails
    old_login_token = auth_service.login("test@example.com", "oldpassword")
    assert old_login_token is None, "Should not be able to login with old password"
    print("✅ Old password login correctly fails")

    # Test invalid token
    invalid_success = auth_service.reset_password("invalid-token", "password")
    assert not invalid_success, "Invalid token should fail"
    print("✅ Invalid token correctly rejected")

    # Test non-existent email
    nonexistent_token = auth_service.initiate_password_reset("nonexistent@example.com")
    assert nonexistent_token is None, "Non-existent email should return None"
    print("✅ Non-existent email correctly handled")

    print("\n🎉 All password reset tests passed!")

if __name__ == "__main__":
    test_password_reset()