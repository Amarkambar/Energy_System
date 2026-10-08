"""
tests/test_auth.py — Unit tests for authentication logic
Run: cd backend && pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
from unittest.mock import patch, MagicMock


# ── Import auth helpers directly ────────────────────────────────────────────
# Patch MongoDB before importing api to avoid connection errors in CI
with patch("pymongo.MongoClient") as mock_client:
    mock_db = MagicMock()
    mock_client.return_value.__getitem__.return_value = mock_db
    import importlib
    import api as _api_module

from api import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("MySecretPass123")
        assert h != "MySecretPass123"

    def test_correct_password_verifies(self):
        h = hash_password("CorrectPass!")
        assert verify_password("CorrectPass!", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("CorrectPass!")
        assert verify_password("WrongPass!", h) is False

    def test_empty_password_differs(self):
        h = hash_password("SomePass123")
        assert verify_password("", h) is False

    def test_hashes_are_unique(self):
        h1 = hash_password("SamePass123")
        h2 = hash_password("SamePass123")
        # bcrypt uses random salt — two hashes should differ
        assert h1 != h2

    def test_hash_length_reasonable(self):
        h = hash_password("TestPass123!")
        assert len(h) >= 20


class TestJWTTokens:
    def test_create_and_verify_token(self):
        token = create_token("user@test.com", "Test User")
        payload = verify_token(token)
        assert payload["email"] == "user@test.com"
        assert payload["name"] == "Test User"

    def test_tampered_token_raises(self):
        from fastapi import HTTPException
        token = create_token("user@test.com", "Test User")
        bad_token = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc:
            verify_token(bad_token)
        assert exc.value.status_code == 401

    def test_empty_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises((HTTPException, Exception)):
            verify_token("")

    def test_none_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises((HTTPException, Exception)):
            verify_token(None)

    def test_token_contains_email(self):
        token = create_token("hello@world.com", "World")
        payload = verify_token(token)
        assert "email" in payload

    def test_different_emails_produce_different_tokens(self):
        t1 = create_token("a@a.com", "A")
        t2 = create_token("b@b.com", "B")
        assert t1 != t2
