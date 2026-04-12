"""Bcrypt implementation of IPasswordHasher."""
import bcrypt
from ...domain.ports import IPasswordHasher


class BcryptHasher(IPasswordHasher):
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
