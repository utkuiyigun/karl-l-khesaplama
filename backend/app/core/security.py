"""
Müşteri API key/secret'ları DB'de plain text saklanmaz.
Bu modül Fernet symmetric encryption sağlar.

KULLANIM:
    encrypted = encrypt_secret("my_api_key")
    decrypted = decrypt_secret(encrypted)

ÖNEMLİ:
- Decrypt edilen değer sadece HTTP çağrısı yaparken kullanılır
- Asla loglanmaz, asla error message'a düşmez
- Variable kullanımı bitince mümkünse silinir (del)
"""
from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.fernet_key.encode())


def encrypt_secret(plain: str) -> str:
    """Plain text → Fernet token (base64)."""
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Fernet token → plain text. Hata fırlatırsa key yanlış demektir."""
    return _fernet.decrypt(token.encode()).decode()
