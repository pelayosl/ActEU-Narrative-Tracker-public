import jwt
import pytest

from app.config import settings
from app.exceptions import InvalidToken, TokenExpired
from app.infrastructure.jwt_handler import JWTHandler


@pytest.fixture
def handler() -> JWTHandler:
    return JWTHandler()


# ---------------------------------------------------------------------------
# encode() / decode() round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_decode_recovers_encoded_payload(self, handler):
        token = handler.encode({"sub": "user-1", "role": "admin"})

        decoded = handler.decode(token)

        assert decoded["sub"] == "user-1"
        assert decoded["role"] == "admin"

    def test_encode_stamps_expiry_claim(self, handler):
        token = handler.encode({"sub": "user-1"})

        decoded = handler.decode(token)
        assert "exp" in decoded

    def test_encode_does_not_mutate_caller_payload(self, handler):
        payload = {"sub": "user-1"}
        handler.encode(payload)
        # The handler copies before adding `exp`; caller's dict stays clean.
        assert payload == {"sub": "user-1"}

    def test_token_is_signed_with_configured_secret(self, handler):
        token = handler.encode({"sub": "user-1"})

        # Decoding with the right secret/alg works...
        jwt.decode(token, settings.JWT_SECRET.get_secret_value(), algorithms=[settings.JWT_ALGORITHM])
        # ...and with a wrong secret it does not.
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, "wrong-secret", algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# decode() — domain exception translation
# ---------------------------------------------------------------------------

class TestDecodeErrors:
    def test_expired_token_raises_token_expired(self, handler, monkeypatch):
        # Mint a token that is already expired.
        monkeypatch.setattr(settings, "JWT_EXPIRATION_MINUTES", -1)
        token = handler.encode({"sub": "user-1"})

        with pytest.raises(TokenExpired):
            handler.decode(token)

    def test_malformed_token_raises_invalid_token(self, handler):
        with pytest.raises(InvalidToken):
            handler.decode("this.is.not.a.jwt")

    def test_wrong_secret_raises_invalid_token(self, handler):
        # Token signed with a different secret → signature verification fails.
        foreign = jwt.encode(
            {"sub": "user-1"}, "another-secret", algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(InvalidToken):
            handler.decode(foreign)

    def test_pyjwt_exceptions_never_leak(self, handler):
        # The service layer must only ever see domain exceptions.
        with pytest.raises((TokenExpired, InvalidToken)):
            handler.decode("garbage")
