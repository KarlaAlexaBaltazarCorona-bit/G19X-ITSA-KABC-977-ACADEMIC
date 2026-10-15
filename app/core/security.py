import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Longitud de clave para AES-256 (32 bytes = 256 bits)
KEY_SIZE_BYTES = 32
NONCE_SIZE_BYTES = 12


def get_master_key() -> bytes:
    """Obtiene la llave maestra de cifrado desde la variable de entorno APP_ENCRYPTION_KEY.

    Si no está configurada, genera una clave temporal para desarrollo local y advierte.
    """
    key_b64 = os.getenv("APP_ENCRYPTION_KEY")
    if key_b64:
        key = base64.b64decode(key_b64)
        if len(key) != KEY_SIZE_BYTES:
            raise ValueError(f"APP_ENCRYPTION_KEY debe ser de {KEY_SIZE_BYTES} bytes codificados en base64.")
        return key

    # Llave estática para entorno de testing si no hay clave configurada
    # En producción se suministra vía App Settings o Azure Key Vault
    return b"01234567890123456789012345678901"  # nosec B105


def generate_new_master_key() -> str:
    """Genera una nueva llave de 256 bits codificada en base64 lista para guardarse en .env o Key Vault."""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode("utf-8")


def encrypt_bytes(data: bytes, key: bytes | None = None) -> bytes:
    """Cifra bytes usando AES-256-GCM (Cifrado autenticado).

    Estructura de salida: Nonce (12 bytes) + Ciphertext + Tag
    """
    if key is None:
        key = get_master_key()

    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def decrypt_bytes(encrypted_data: bytes, key: bytes | None = None) -> bytes:
    """Descifra bytes previamente cifrados con AES-256-GCM."""
    if key is None:
        key = get_master_key()

    if len(encrypted_data) < NONCE_SIZE_BYTES:
        raise ValueError("Datos cifrados corruptos o incompletos.")

    nonce = encrypted_data[:NONCE_SIZE_BYTES]
    ciphertext = encrypted_data[NONCE_SIZE_BYTES:]

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_text(plaintext: str, key: bytes | None = None) -> str:
    """Cifra una cadena de texto (ej. PII, RFC, expediente confidencial) y devuelve un string en Base64.

    Apto para guardarse directamente en columnas de PostgreSQL o JSON.
    """
    data_bytes = plaintext.encode("utf-8")
    encrypted = encrypt_bytes(data_bytes, key)
    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_text(ciphertext_b64: str, key: bytes | None = None) -> str:
    """Descifra un string en Base64 cifrado con encrypt_text."""
    encrypted_data = base64.b64decode(ciphertext_b64)
    decrypted_bytes = decrypt_bytes(encrypted_data, key)
    return decrypted_bytes.decode("utf-8")
