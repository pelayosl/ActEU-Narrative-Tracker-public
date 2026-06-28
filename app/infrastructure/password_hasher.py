import bcrypt

class PasswordHasher:
    """Adapter over bcrypt for hashing and verifying passwords."""

    def hash(self, password: str) -> str:
        """Hash a plaintext password with a freshly generated bcrypt salt.

        :param password: The plaintext password.
        :returns: The bcrypt hash as a string suitable for storage.
        """
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, password: str, hashed: str) -> bool:
        """Check a plaintext password against a stored bcrypt hash.

        :param password: The plaintext password to verify.
        :param hashed: The previously stored bcrypt hash.
        :returns: ``True`` if the password matches, ``False`` otherwise.
        """
        return bcrypt.checkpw(password.encode(), hashed.encode())
