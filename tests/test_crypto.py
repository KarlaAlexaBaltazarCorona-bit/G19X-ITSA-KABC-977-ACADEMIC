from app.core.security import decrypt_text, encrypt_text, generate_new_master_key


def test_encryption_decryption_flow():
    secret_text = "Expediente Legal Confidencial #98432 - Juan Perez"
    ciphertext = encrypt_text(secret_text)

    # Asegurar que el texto cifrado es diferente al original
    assert ciphertext != secret_text

    # Asegurar que se descifra correctamente
    decrypted = decrypt_text(ciphertext)
    assert decrypted == secret_text


def test_custom_key_generation():
    key_b64 = generate_new_master_key()
    assert isinstance(key_b64, str)
    assert len(key_b64) > 30


def test_different_nonces_produce_different_ciphertexts():
    text = "Mismo texto"
    c1 = encrypt_text(text)
    # Por seguridad, dos cifrados del mismo texto con AES-GCM
    # deben tener nonces distintos y por tanto ciphertexts distintos
    c2 = encrypt_text(text)

    assert c1 != c2
    assert decrypt_text(c1) == text
    assert decrypt_text(c2) == text
