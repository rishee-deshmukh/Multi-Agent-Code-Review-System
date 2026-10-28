import hashlib
import hmac


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()  # @label weak_crypto medium -- fast unsalted hash used for passwords


def verify_password(password: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), stored_hash)


def register(users: dict, name: str, password: str) -> None:
    if name in users:
        raise ValueError("user exists")
    users[name] = hash_password(password)
