import secrets
import hashlib

def generate_api_key() -> tuple[str, str, str]:
    """
    Ek genuine original API key generate karta hai.
    Returns: (raw_key, key_hash, prefix)
    """
    token = secrets.token_urlsafe(32)
    raw_key = f"sk_live_{token}"
    prefix = raw_key[:10]  # 'sk_live_...'
    
    # Database mein secure rakhne ke liye hash karte hain
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash, prefix

def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()
