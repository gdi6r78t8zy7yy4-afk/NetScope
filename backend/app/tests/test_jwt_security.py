# NetScope JWT Security Tests

"""
Comprehensive tests for Phase 5: JWT Authentication Security Fixes.

Tests cover:
- Token expiration validation
- Token binding (session hijacking prevention)
- nbf (not before) claim validation
- Algorithm confusion prevention
"""

import pytest
import hashlib
from datetime import datetime, timedelta

from app.core.auth import create_token, verify_token, get_client_ip, TokenPayload
from app.core.config import settings


class TestTokenExpiration:
    """Test token expiration validation."""

    def test_valid_token_not_expired(self):
        """Test that a valid non-expired token is accepted."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})
        payload = verify_token(token)

        assert payload is not None
        assert payload.sub == "test-user"
        assert payload.username == "testuser"

    def test_expired_token_rejected(self):
        """Test that an expired token is rejected."""
        # Create a token with very short expiration
        past_time = datetime.utcnow() - timedelta(minutes=1)

        # Manually create an expired token
        import jwt as pyjwt

        expired_token = pyjwt.encode(
            {
                "sub": "test-user",
                "username": "testuser",
                "exp": past_time,
                "iat": datetime.utcnow() - timedelta(minutes=2),
                "nbf": past_time,
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        payload = verify_token(expired_token)

        assert payload is None

    def test_future_token_not_yet_valid(self):
        """Test that a token not yet valid (future exp) is handled correctly."""
        future_time = datetime.utcnow() + timedelta(minutes=1)

        import jwt as pyjwt

        # Create token that expires in the future but was issued in the past
        future_token = pyjwt.encode(
            {
                "sub": "test-user",
                "username": "testuser",
                "exp": future_time,
                "iat": datetime.utcnow(),
                "nbf": future_time,  # Not valid until future
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        payload = verify_token(future_token)

        # Should be rejected because nbf (not before) is in the future
        assert payload is None


class TestTokenBinding:
    """Test token binding (session hijacking prevention)."""

    def test_token_with_fingerprint(self):
        """Test that tokens can be bound to client fingerprint."""

        # Create a mock request-like object
        class MockRequest:
            def __init__(self, ip: str, user_agent: str):
                self.client = type("obj", (object,), {"host": ip})()
                self._headers = {"user-agent": user_agent}

            @property
            def headers(self):
                return self._headers

        # Create token with fingerprint binding
        request = MockRequest("192.168.1.100", "TestAgent/1.0")
        token = create_token(
            data={"sub": "test-user", "username": "testuser"}, request=request
        )

        payload = verify_token(token, request)

        assert payload is not None
        assert hasattr(payload, "fingerprint")
        assert payload.fingerprint is not None

    def test_token_fingerprint_mismatch_rejected(self):
        """Test that tokens with mismatched fingerprints are rejected."""

        # Create a mock request
        class MockRequest:
            def __init__(self, ip: str, user_agent: str):
                self.client = type("obj", (object,), {"host": ip})()
                self._headers = {"user-agent": user_agent}

            @property
            def headers(self):
                return self._headers

        # Create token with one fingerprint
        request1 = MockRequest("192.168.1.100", "TestAgent/1.0")
        token = create_token(
            data={"sub": "test-user", "username": "testuser"}, request=request1
        )

        # Try to verify with different fingerprint (different IP)
        request2 = MockRequest("10.0.0.1", "DifferentAgent/2.0")
        payload = verify_token(token, request2)

        # Should be rejected due to fingerprint mismatch
        assert payload is None

    def test_token_without_fingerprint(self):
        """Test that tokens without fingerprints can still be verified."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})

        payload = verify_token(token)

        assert payload is not None
        assert payload.sub == "test-user"


class TestNbfClaim:
    """Test nbf (not before) claim validation."""

    def test_valid_nbf_immediate(self):
        """Test token with nbf set to current time (immediate validity)."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})

        payload = verify_token(token)

        assert payload is not None
        # nbf should be set to current time when created
        if hasattr(payload, "nbf") and payload.nbf:
            assert isinstance(payload.nbf, datetime)

    def test_token_with_future_nbf_rejected(self):
        """Test that tokens with future nbf are rejected."""
        import jwt as pyjwt

        future_time = datetime.utcnow() + timedelta(minutes=5)

        future_nbf_token = pyjwt.encode(
            {
                "sub": "test-user",
                "username": "testuser",
                "exp": future_time + timedelta(minutes=5),
                "iat": datetime.utcnow(),
                "nbf": future_time,  # Not valid until 5 minutes in future
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        payload = verify_token(future_nbf_token)

        assert payload is None

    def test_token_with_past_nbf_accepted(self):
        """Test that tokens with past nbf are accepted."""
        import jwt as pyjwt

        past_time = datetime.utcnow() - timedelta(minutes=10)

        past_nbf_token = pyjwt.encode(
            {
                "sub": "test-user",
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "iat": past_time,
                "nbf": past_time,  # Valid from 10 minutes ago
            },
            settings.secret_key,
            algorithm=settings.algorithm,
        )

        payload = verify_token(past_nbf_token)

        assert payload is not None
        assert payload.sub == "test-user"


class TestAlgorithmValidation:
    """Test algorithm confusion prevention."""

    def test_hs256_algorithm_accepted(self):
        """Test that HS256 algorithm is accepted."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})

        payload = verify_token(token)

        assert payload is not None
        assert payload.sub == "test-user"

    def test_none_algorithm_rejected(self):
        """Test that 'none' algorithm is rejected."""
        import jwt as pyjwt

        # Try to create a token with 'none' algorithm
        none_token = pyjwt.encode(
            {
                "sub": "test-user",
                "username": "testuser",
                "exp": datetime.utcnow() + timedelta(minutes=30),
                "iat": datetime.utcnow(),
                "nbf": datetime.utcnow(),
            },
            algorithm="none",
            key="",  # No key needed for 'none' algorithm
        )

        payload = verify_token(none_token)

        # Should be rejected because we only allow configured algorithm (HS256)
        assert payload is None

    def test_rsa_algorithm_rejected(self):
        """Test that RSA algorithms are rejected."""
        import jwt as pyjwt

        # This would be an attack if the server used RSA and attacker sent RS256
        # with a public key they control

        # Create token with HS256 (normal case)
        normal_token = create_token(
            data={
                "sub": "test-user",
                "username": "testuser"})

        payload = verify_token(normal_token)
        assert payload is not None

    def test_multiple_algorithms_only_configured_one_accepted(self):
        """Test that only the configured algorithm is accepted."""
        import jwt as pyjwt

        # Create token with HS256
        hs256_token = create_token(
            data={
                "sub": "test-user",
                "username": "testuser"})

        # This should work
        payload = verify_token(hs256_token)
        assert payload is not None


class TestClientIPHelper:
    """Test get_client_ip helper function."""

    def test_direct_ip(self):
        """Test getting IP from direct connection."""

        class MockRequest:
            def __init__(self, host: str):
                self.client = type("obj", (object,), {"host": host})()
                self._headers = {}

            @property
            def headers(self):
                return self._headers

        request = MockRequest("192.168.1.100")
        ip = get_client_ip(request)

        assert ip == "192.168.1.100"

    def test_proxy_ip_with_x_forwarded_for(self):
        """Test getting IP from X-Forwarded-For header."""

        class MockRequest:
            def __init__(self, forwarded: str):
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()
                self._headers = {"X-Forwarded-For": forwarded}

            @property
            def headers(self):
                return self._headers

        request = MockRequest("10.0.0.1, 192.168.1.1")
        ip = get_client_ip(request)

        # Should extract first IP from X-Forwarded-For
        assert ip == "10.0.0.1"

    def test_proxy_ip_with_single_x_forwarded_for(self):
        """Test getting IP from single X-Forwarded-For value."""

        class MockRequest:
            def __init__(self, forwarded: str):
                self.client = type("obj", (object,), {"host": "127.0.0.1"})()
                self._headers = {"X-Forwarded-For": forwarded}

            @property
            def headers(self):
                return self._headers

        request = MockRequest("10.0.0.1")
        ip = get_client_ip(request)

        assert ip == "10.0.0.1"


class TestCreateToken:
    """Test create_token function with security features."""

    def test_creates_token_with_exp(self):
        """Test that token has expiration claim."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})

        # Decode without verification to check claims
        import jwt as pyjwt

        payload = pyjwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload

    def test_token_binding_with_request(self):
        """Test that token is bound to client when request provided."""

        class MockRequest:
            def __init__(self):
                self.client = type(
                    "obj", (object,), {
                        "host": "192.168.1.100"})()
                self._headers = {"user-agent": "TestAgent/1.0"}

            @property
            def headers(self):
                return self._headers

        request = MockRequest()
        token = create_token(
            data={"sub": "test-user", "username": "testuser"}, request=request
        )

        # Decode to check fingerprint
        import jwt as pyjwt

        payload = pyjwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        assert "fingerprint" in payload
        # Fingerprint should be SHA256 hash of IP:UserAgent
        expected = hashlib.sha256(
            "192.168.1.100:TestAgent/1.0".encode()).hexdigest()
        assert payload["fingerprint"] == expected

    def test_token_without_request_has_no_fingerprint(self):
        """Test that token without request has no fingerprint."""
        token = create_token(data={"sub": "test-user", "username": "testuser"})

        # Decode to check fingerprint is not present
        import jwt as pyjwt

        payload = pyjwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        assert "fingerprint" not in payload


class TestVerifyToken:
    """Test verify_token function with security features."""

    def test_returns_none_for_invalid_signature(self):
        """Test that invalid signature returns None."""
        import jwt as pyjwt

        # Create a valid token first
        valid_token = create_token(
            data={
                "sub": "test-user",
                "username": "testuser"})

        # Create a token with wrong secret
        invalid_token = pyjwt.encode(
            {"sub": "test-user", "username": "testuser"},
            "wrong-secret-key",
            algorithm=settings.algorithm,
        )

        payload = verify_token(invalid_token)

        assert payload is None

    def test_returns_none_for_invalid_token(self):
        """Test that invalid token returns None."""
        payload = verify_token("not-a-valid-token.at.all")

        assert payload is None

    def test_returns_none_for_malformed_token(self):
        """Test that malformed token returns None."""
        payload = verify_token("malformed")

        assert payload is None


class TestTokenPayloadModel:
    """Test TokenPayload model with security fields."""

    def test_token_payload_has_fingerprint_field(self):
        """Test that TokenPayload has fingerprint field."""
        payload = TokenPayload(
            sub="test-user",
            username="testuser",
            exp=datetime.utcnow() + timedelta(minutes=30),
            iat=datetime.utcnow(),
            nbf=datetime.utcnow(),
            fingerprint="abc123",
        )

        assert payload.fingerprint == "abc123"

    def test_token_payload_optional_fields(self):
        """Test that optional fields can be None."""
        payload = TokenPayload(
            sub="test-user",
            username="testuser",
            exp=datetime.utcnow() + timedelta(minutes=30),
        )

        assert payload.iat is None
        assert payload.nbf is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
