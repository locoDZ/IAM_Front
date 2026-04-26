import os
import json
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Master secret key for KDC (in production, load from env)
MASTER_KEY = os.environ.get("KDC_MASTER_KEY", "securecorp-master-key-2024-secret!")
FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(MASTER_KEY.encode()).digest())
fernet = Fernet(FERNET_KEY)

# Session key registry (in-memory, maps key_id -> session_key)
session_keys: dict = {}


def generate_session_key() -> bytes:
    """Generate a random 32-byte session key."""
    return os.urandom(32)


def encrypt_ticket(payload: dict) -> str:
    """Encrypt a ticket payload using Fernet (AES-128-CBC + HMAC)."""
    data = json.dumps(payload).encode()
    token = fernet.encrypt(data)
    return token.decode()


def decrypt_ticket(token: str) -> dict:
    """Decrypt and verify a ticket. Raises on tamper or expiry."""
    data = fernet.decrypt(token.encode())
    return json.loads(data.decode())


def encrypt_with_session_key(payload: dict, session_key: bytes) -> str:
    """Encrypt data with a session key (AES-256-CBC)."""
    iv = os.urandom(16)
    data = json.dumps(payload).encode()

    # Pad data
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    result = {
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }
    return base64.b64encode(json.dumps(result).encode()).decode()


def decrypt_with_session_key(encrypted: str, session_key: bytes) -> dict:
    """Decrypt data with a session key (AES-256-CBC)."""
    raw = json.loads(base64.b64decode(encrypted).decode())
    iv = base64.b64decode(raw["iv"])
    ciphertext = base64.b64decode(raw["ciphertext"])

    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded) + unpadder.finalize()
    return json.loads(data.decode())


def generate_ticket_id() -> str:
    """Generate a unique ticket ID."""
    return base64.urlsafe_b64encode(os.urandom(16)).decode()


def hash_password(password: str) -> str:
    """Hash a password with SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hmac.compare_digest(hash_password(password), hashed)


def build_tgt(username: str, user_data: dict, session_key: bytes) -> dict:
    """Build a TGT payload."""
    now = datetime.utcnow()
    return {
        "type": "TGT",
        "ticket_id": generate_ticket_id(),
        "username": username,
        "role": user_data["role"],
        "department": user_data["department"],
        "clearance": user_data["clearance"],
        "session_key": base64.b64encode(session_key).decode(),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=8)).isoformat(),
    }


def build_service_ticket(username: str, user_data: dict, service: str, session_key: bytes) -> dict:
    """Build a Service Ticket payload."""
    now = datetime.utcnow()
    return {
        "type": "SERVICE_TICKET",
        "ticket_id": generate_ticket_id(),
        "username": username,
        "role": user_data["role"],
        "department": user_data["department"],
        "clearance": user_data["clearance"],
        "service": service,
        "session_key": base64.b64encode(session_key).decode(),
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "location": user_data.get("location", "internal"),
    }


def is_expired(expires_at: str) -> bool:
    """Check if a ticket is expired."""
    expiry = datetime.fromisoformat(expires_at)
    return datetime.utcnow() > expiry
