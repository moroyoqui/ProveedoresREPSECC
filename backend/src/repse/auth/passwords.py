"""Local password hashing & verification (argon2).

Per constitution principle I, passwords are hashed with a modern algorithm.
argon2 is the OWASP-recommended default and is already in our dependencies
(passlib[argon2]).
"""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    if len(plain) < 8:
        raise ValueError("Password must be at least 8 characters")
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return _pwd_ctx.verify(plain, hashed)
    except (ValueError, TypeError):
        return False
